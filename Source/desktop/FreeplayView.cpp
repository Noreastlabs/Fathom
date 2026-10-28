#include "desktop/Appearance.hpp"
#include "desktop/FreeplayView.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"

#include <chrono>
#include <iomanip>
#include <sstream>
#include <thread>
#include <utility>

namespace fathom::desktop {

namespace {
std::uint64_t monotonicNanoseconds() noexcept {
    const auto now = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(now).count());
}

json::Value rational(std::int64_t numerator, std::int64_t denominator = 1) {
    return json::Value::Array{json::Value::fromInteger(numerator), json::Value::fromInteger(denominator)};
}
}

FreeplayView::FreeplayView() {
    heading.setText(juce::String::fromUTF8("FREEPLAY — SEPARATE LOCAL ACTIVITY"), juce::dontSendNotification);
    heading.setFont(juce::FontOptions{34.0f, juce::Font::bold});
    heading.setColour(juce::Label::textColourId, appearance::colour(0xff6bd5cb));
    explanation.setComponentID("freeplay-explanation");
    explanation.setTitle("Read-only Freeplay entry: separate active time/history, shared Audio and no curriculum credit.");
    const auto fullExplanation = juce::String{
        "A standalone practice space with no lesson or curriculum prerequisite. Without a configured local profile, Start and Stop only demonstrate the timer: Stop cannot save Freeplay history and no curriculum progress is created.\n\n"
        "Stopped Freeplay activity is saved locally as separate history and never grants curriculum progress. Use Audio settings for shared speakers and headphones; open Audio settings without starting sound. Open rhythm tools explicitly when you are ready.\n\n"
        "Start counts active time. Pause retains active time without recording history. Stop requests one separate local Freeplay history save when a local profile is configured; Back and rhythm tools wait until that save is confirmed. For a disposable Development Preview profile, launch with --capture-preview <new private directory> <IANA timezone>."};
    explanation.setText(
        "Freeplay has no lesson prerequisite and grants no curriculum credit. Start counts active time; Pause retains it; Stop saves separate local history only with a configured profile.\n"
        "Open Audio settings without starting sound. Open rhythm tools explicitly after Pause or Stop.",
        juce::dontSendNotification);
    explanation.setDescription(fullExplanation);
    explanation.setHelpText(fullExplanation);
    explanation.setTooltip(fullExplanation);
    explanation.setFont(juce::FontOptions{17.0f});
    explanation.setJustificationType(juce::Justification::topLeft);
    timerCaption.setText("Active Freeplay time", juce::dontSendNotification);
    timerCaption.setFont(juce::FontOptions{16.0f, juce::Font::bold});
    timer_.setFont(juce::FontOptions{42.0f, juce::Font::bold});
    timer_.setColour(juce::Label::textColourId, appearance::colour(0xfff2f7f8));
    timer_.setText(formatDuration(0), juce::dontSendNotification);
    status_.setFont(juce::FontOptions{15.0f});
    status_.setColour(juce::Label::textColourId, appearance::colour(0xffa9bbc5));
    status_.setJustificationType(juce::Justification::topLeft);
    setStatus("Freeplay is stopped; Opening Freeplay does not start sound. Back is safe now, and this view has no new local history until Start and Stop are completed. No activity has been recorded yet. Stop saves one local Freeplay history entry when a local profile is configured; Freeplay never grants curriculum progress. Open Progress after the save is confirmed to review the finalized Freeplay record read-only. Next action: choose Start freeplay to begin active-time capture; Stop saves one separate local Freeplay history entry when a local profile is configured. For a disposable Development Preview profile, launch with --capture-preview <new private directory> <IANA timezone>. Without a configured local profile, Start and Stop only demonstrate the timer: Stop cannot save Freeplay history and no curriculum progress is created.",
              juce::dontSendNotification,
              "Stopped; no sound or activity started. Choose Start freeplay to begin active time. Stop saves separate local history only with a configured profile; Back is safe now.");
    profileState_.setComponentID("freeplay-profile-state");
    profileState_.setTitle("Freeplay local-profile boundary marker.");
    profileState_.setFont(juce::FontOptions{15.0f, juce::Font::bold});
    profileState_.setColour(juce::Label::textColourId, appearance::colour(0xffffd479));
    profileState_.setText("No local profile configured; Freeplay history stays unsaved.", juce::dontSendNotification);

    for (juce::Component* component : {static_cast<juce::Component*>(&heading), static_cast<juce::Component*>(&explanation),
                                       static_cast<juce::Component*>(&timerCaption), static_cast<juce::Component*>(&timer_),
                                       static_cast<juce::Component*>(&status_), static_cast<juce::Component*>(&profileState_), static_cast<juce::Component*>(&startButton),
                                       static_cast<juce::Component*>(&pauseButton), static_cast<juce::Component*>(&stopButton),
                                       static_cast<juce::Component*>(&retryButton),
                                       static_cast<juce::Component*>(&rhythmButton), static_cast<juce::Component*>(&progressButton),
                                       static_cast<juce::Component*>(&audioButton),
                                       static_cast<juce::Component*>(&backButton)})
        addAndMakeVisible(*component);

    startButton.setComponentID("freeplay-start");
    startButton.setTitle("Start Freeplay and begin active-time capture");
    pauseButton.setComponentID("freeplay-pause");
    pauseButton.setTitle("Pause Freeplay and retain active time without saving history");
    stopButton.setComponentID("freeplay-stop");
    stopButton.setTitle("Stop Freeplay and save one separate local history record when configured");
    retryButton.setComponentID("freeplay-retry-save");
    retryButton.setTitle("Retry the retained Freeplay history save without starting another activity");
    rhythmButton.setComponentID("freeplay-rhythm-tools");
    rhythmButton.setTitle("Open rhythm tools while Freeplay is paused or stopped; unsaved active time stays retained");
    progressButton.setComponentID("freeplay-open-progress");
    progressButton.setTitle("Review saved Freeplay history in read-only Progress");
    audioButton.setComponentID("freeplay-audio-settings");
    audioButton.setTitle("Open shared Audio settings without starting sound");
    backButton.setComponentID("freeplay-back");
    backButton.setTitle("Return to Home after Freeplay is safely stopped");
    status_.setComponentID("freeplay-status");
    status_.setTitle("Read-only Freeplay lifecycle, active time, save boundary and next action.");
    int focusOrder = 1;
    for (auto* button : {&startButton, &pauseButton, &stopButton, &rhythmButton, &progressButton, &audioButton, &backButton, &retryButton}) {
        button->setWantsKeyboardFocus(true);
        button->setExplicitFocusOrder(focusOrder++);
        button->setColour(juce::TextButton::buttonColourId, appearance::colour(0xff6bd5cb));
        button->setColour(juce::TextButton::textColourOffId, appearance::colour(0xff10212c));
        button->setColour(juce::TextButton::textColourOnId, appearance::colour(0xff10212c));
    }
    startButton.onClick = [this] { startFreeplay(); };
    pauseButton.onClick = [this] { pauseFreeplay(); };
    stopButton.onClick = [this] { stopFreeplay(); };
    retryButton.onClick = [this] { retryPersistence(); };
    rhythmButton.onClick = [this] { handleRhythmTools(); };
    progressButton.onClick = [this] { handleProgress(); };
    audioButton.onClick = [this] { handleAudioSettings(); };
    backButton.onClick = [this] { handleBack(); };
    startTimer(50);
    refresh();
}

FreeplayView::~FreeplayView() {
    stopTimer();
}

void FreeplayView::setStatus(juce::String detail, juce::NotificationType, juce::String visible) {
    statusDetail_ = detail.toStdString();
    status_.setText(visible.isNotEmpty() ? visible : detail, juce::dontSendNotification);
    status_.setDescription(detail);
    status_.setHelpText(detail);
    status_.setTooltip(detail);
}

void FreeplayView::setClockForTest(std::function<std::uint64_t()> clock) {
    clock_ = std::move(clock);
    refresh();
}

bool FreeplayView::configureStore(storage::ProfileStore& store, std::function<std::string()> utcNow,
                                  std::string timezone) {
    if (running_ || paused_ || persistencePending_ || persistenceBlocked_
        || (capture_ && !capture_->canLeave(true)) || !utcNow || timezone.empty())
        return false;
    storage::validateUtc(utcNow());
    storage::localDay(utcNow(), timezone);
    store_ = &store;
    utcNow_ = std::move(utcNow);
    timezone_ = std::move(timezone);
    refresh();
    return true;
}

std::uint64_t FreeplayView::nowNanoseconds() const noexcept {
    return clock_ ? clock_() : monotonicNanoseconds();
}

std::uint64_t FreeplayView::activeNanoseconds() const noexcept {
    if (!running_)
        return accumulatedNanoseconds_;
    const auto now = nowNanoseconds();
    return accumulatedNanoseconds_ + (now >= startedNanoseconds_ ? now - startedNanoseconds_ : 0);
}

std::string FreeplayView::formatDuration(const std::uint64_t nanoseconds) {
    const auto totalSeconds = nanoseconds / 1000000000ULL;
    const auto hours = totalSeconds / 3600ULL;
    const auto minutes = (totalSeconds / 60ULL) % 60ULL;
    const auto seconds = totalSeconds % 60ULL;
    std::ostringstream text;
    text << std::setfill('0') << std::setw(2) << hours << ':' << std::setw(2) << minutes << ':' << std::setw(2) << seconds;
    return text.str();
}

bool FreeplayView::startFreeplay() {
    if (running_ || persistencePending_ || persistenceBlocked_
        || (capture_ && !capture_->canLeave(true)) || coordinator_.pending())
        return false;
    if (!paused_) {
        // A stopped activity is terminal. Only an explicit new Start may clear
        // its duration, after the existing capture confirms ownership release.
        if (capture_ && capture_->phase() == capture::SessionPhase::Saved
            && !capture_->again(true))
            return false;
        capture_.reset();
        accumulatedNanoseconds_ = 0;
        persistedNanoseconds_ = 0;
        persistenceSaved_ = false;
        persistenceStatus_.clear();
        stopped_ = false;
    }
    startedNanoseconds_ = nowNanoseconds();
    running_ = true;
    paused_ = false;
    setStatus("Freeplay timer running. Stop is required to create one separate local history record; Freeplay never grants curriculum progress. Rhythm output remains stopped until you open it explicitly. Pause retains active time without recording history.",
                    juce::dontSendNotification);
    refresh();
    return true;
}

bool FreeplayView::pauseFreeplay() {
    if (!running_)
        return false;
    accumulatedNanoseconds_ = activeNanoseconds();
    running_ = false;
    paused_ = true;
    setStatus("Freeplay paused. Active time retained; inactive time is not counted. Stop remains required to create one separate local history record; Back to Home, rhythm tools, Audio settings and Progress are available while paused; they retain this unsaved active time and do not save it. Return to Freeplay and Resume to continue. Stop requests history only with a configured local profile.", juce::dontSendNotification);
    refresh();
    return true;
}

bool FreeplayView::stopFreeplay() {
    if (stopped_ || persistencePending_ || persistenceBlocked_ || (!running_ && !paused_))
        return false;
    if (running_)
        accumulatedNanoseconds_ = activeNanoseconds();
    running_ = false;
    paused_ = false;
    stopped_ = true;
    beginPersistence();
    if (!persistencePending_ && persistenceStatus_.empty())
        persistenceStatus_ = "Freeplay stopped. Active time retained; no activity history was saved.";
    setStatus(persistenceStatus_, juce::dontSendNotification);
    refresh();
    return true;
}

bool FreeplayView::retryPersistence() {
    if(exitDiscard_){retryExitDiscard();return true;}
    if (!retrySaveAvailable()) {
        if (capture_ && !persistencePending_ && !persistenceSaved_) {
            persistenceStatus_ = "Freeplay history cannot be retried through this view while the stopped duration is not bound to the original allocation. Keep this profile and use the existing recovery path; the active time and unresolved operation remain retained.";
            setStatus(persistenceStatus_, juce::dontSendNotification);
            refresh();
        }
        return false;
    }
    try {
        if (!capture_) {
            beginPersistence();
            refresh();
            return persistencePending_;
        }
        const auto now = monotonicMilliseconds();
        const bool retried = capture_->retry(now);
        if (!retried) {
            setStatus("The retained Freeplay history operation is not ready for retry. Keep this profile and use the existing recovery path; unresolved ownership cannot be replaced by a new activity.",
                      juce::dontSendNotification);
            return false;
        }
        if (capture_->phase() == capture::SessionPhase::Idle) {
            // The existing capture permits this only after proving allocation
            // absent. Retain the stopped duration; do not resume the timer.
            capture::StartRequest request;
            if (!freeplayConfiguration(request)
                || !capture_->start(std::move(request), ++commandSequence_, now))
                throw std::runtime_error("Freeplay retained history allocation retry was refused");
        }
        persistencePending_ = true;
        persistenceBlocked_ = false;
        persistenceStatus_ = "Retrying the retained Freeplay history save; active time remains stopped.";
        setStatus(persistenceStatus_, juce::dontSendNotification);
        refresh();
        return true;
    } catch (const std::exception& error) {
        persistenceBlocked_ = capture_ && !capture_->canLeave(true);
        persistenceStatus_ = std::string("Freeplay history retry is unresolved; original operation retained: ") + error.what();
        setStatus(persistenceStatus_, juce::dontSendNotification);
        refresh();
        return false;
    }
}

FreeplayView::CloseState FreeplayView::closeState() const {
    if (persistencePending_)
        return CloseState::Pending;
    if (persistenceBlocked_ || (capture_ && !capture_->canLeave(true))
        || (stopped_ && persistenceConfigured() && !persistenceSaved_))
        return CloseState::Blocked;
    if (running_ || paused_)
        return CloseState::Pending;
    return CloseState::Ready;
}

bool FreeplayView::requestExit(bool discard){
 if(!discard)return requestClose();
 exitDiscard_=true;
 if(running_)accumulatedNanoseconds_=activeNanoseconds();
 running_=false;paused_=false;stopped_=true;
 if(!capture_)return true; // volatile timer only; never beginPersistence
 capture_->requestExitDiscard();
 if(utcNow_)capture_->poll(monotonicMilliseconds(),utcNow_());
 return capture_->canLeaveForExit(true,monotonicMilliseconds());
}
bool FreeplayView::requestClose() {
    if (running_ || paused_)
        stopFreeplay();
    // This polls ready futures only. A repeated Quit neither begins a new
    // allocation nor retries a failed original save on the user's behalf.
    servicePersistence();
    return closeState() == CloseState::Ready;
}

std::uint64_t FreeplayView::stoppedFrames() const {
    return static_cast<std::uint64_t>((static_cast<__int128>(persistedNanoseconds_)
                                      * coordinator_.configuration().rate) / 1000000000ULL);
}

bool FreeplayView::retrySaveAvailable() const {
    if (!stopped_ || running_ || paused_ || persistencePending_ || persistenceSaved_ || !store_ || !utcNow_)
        return false;
    if (!capture_)
        return true;
    switch (capture_->phase()) {
        case capture::SessionPhase::Failed:
        case capture::SessionPhase::SealedCheckpoint:
            return true;
        case capture::SessionPhase::Review:
            return coordinator_.activeFrames() == stoppedFrames();
        default:
            // Allocation inspection enters canceled Review with zero frames in
            // the unchanged capture API. It cannot bind this view's stopped
            // timer, so keep its original owner/debt instead of saving zero.
            return false;
    }
}

void FreeplayView::handleBack() {
    requestBack();
}

void FreeplayView::handleRhythmTools() {
    requestRhythmTools();
}

void FreeplayView::handleProgress() {
    requestProgress();
}

void FreeplayView::handleAudioSettings() {
    requestAudioSettings();
}

bool FreeplayView::requestBack() {
    if (running_) {
        setStatus("Pause or stop Freeplay before leaving; active time remains retained.", juce::dontSendNotification);
        return false;
    }
    if (persistencePending_) {
        setStatus("Freeplay history is still being saved locally; remain here until it is confirmed.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistenceBlocked_) {
        setStatus("Freeplay history is unresolved; retain this profile and use the existing recovery path.",
                        juce::dontSendNotification);
        return false;
    }
    if (onBack)
        onBack();
    else
        setStatus("Back is unavailable from Freeplay until the existing Home route is connected. No Freeplay activity or history was changed.",
                        juce::dontSendNotification);
    return static_cast<bool>(onBack);
}

bool FreeplayView::requestRhythmTools() {
    if (running_) {
        setStatus("Pause or stop Freeplay before opening rhythm tools; active time remains retained.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistencePending_) {
        setStatus("Freeplay history is still being saved locally; remain here until it is confirmed.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistenceBlocked_) {
        setStatus("Freeplay history is unresolved; retain this profile and use the existing recovery path.",
                        juce::dontSendNotification);
        return false;
    }
    if (onRhythmTools)
        onRhythmTools();
    else
        setStatus("Rhythm tools are unavailable from Freeplay until the existing rhythm-tools page is connected. Return to Home and choose Metronome or Rhythm preview; no sound was started.",
                        juce::dontSendNotification);
    return static_cast<bool>(onRhythmTools);
}

bool FreeplayView::requestProgress() {
    if (running_) {
        setStatus("Pause or stop Freeplay before opening Progress; active time remains retained.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistencePending_) {
        setStatus("Freeplay history is still being saved locally; remain here until it is confirmed.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistenceBlocked_) {
        setStatus("Freeplay history is unresolved; retain this profile and use the existing recovery path.",
                        juce::dontSendNotification);
        return false;
    }
    if (onProgress)
        onProgress();
    else
        setStatus("Progress is unavailable from Freeplay until the existing Progress page is connected. Return to Home and choose Progress to review saved local activity; no activity or curriculum credit was created.",
                        juce::dontSendNotification);
    return static_cast<bool>(onProgress);
}

bool FreeplayView::requestAudioSettings() {
    if (running_) {
        setStatus("Pause or stop Freeplay before opening Audio settings; active time remains retained.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistencePending_) {
        setStatus("Freeplay history is still being saved locally; remain here until it is confirmed.",
                        juce::dontSendNotification);
        return false;
    }
    if (persistenceBlocked_) {
        setStatus("Freeplay history is unresolved; retain this profile and use the existing recovery path.",
                        juce::dontSendNotification);
        return false;
    }
    if (onAudioSettings)
        onAudioSettings();
    else
        setStatus("Audio settings are unavailable from Freeplay until the existing shared Audio page is connected. Return to Home and choose Audio settings; no sound was started.",
                        juce::dontSendNotification);
    return static_cast<bool>(onAudioSettings);
}

void FreeplayView::timerCallback() {
    servicePersistence();
    if (!persistenceStatus_.empty())
        setStatus(persistenceStatus_, juce::dontSendNotification);
    refresh();
}

std::int64_t FreeplayView::monotonicMilliseconds() noexcept {
    const auto now = std::chrono::steady_clock::now().time_since_epoch();
    return static_cast<std::int64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(now).count());
}

bool FreeplayView::freeplayConfiguration(capture::StartRequest& request) {
    if (!store_ || !utcNow_ || timezone_.empty())
        return false;
    practice::Configuration configuration;
    configuration.rate = 44100;
    configuration.bpm = 120;
    configuration.span = Rational{1};
    configuration.countIn = practice::CountIn::Off;
    configuration.meter = std::pair<int, int>{4, 4};
    configuration.faithfulWholeSpan = true;
    configuration.targetCycles = 1000000;
    const auto values = capture::configurationValues(configuration);
    const auto settings = json::Value::Object{{"values", values}, {"synthetic_fixture", false},
                                               {"authored_tempo_ref", nullptr}, {"beat_reference_q", rational(1)}};
    capture::Binding binding;
    binding.kind = "FreeplayActivity";
    binding.context = json::Value::Object{{"configuration_version", json::Value::fromInteger(1)},
                                          {"configuration", settings}};
    binding.sourceHashes = nullptr;
    binding.practiceUtc = utcNow_();
    binding.timezone = timezone_;
    request = {std::move(binding), configuration, 1};
    return true;
}

practice::Progress FreeplayView::freeplayProgress(const std::uint64_t frames) const {
    practice::Progress progress;
    progress.owner = coordinator_.owner();
    progress.sequence = 1;
    progress.clientAcceptedThrough = frames;
    progress.scheduledThrough = frames;
    progress.uncertainThrough = frames;
    progress.activeFrames = frames;
    scheduler::FrameRatio cycle;
    scheduler::samples(coordinator_.configuration().span, coordinator_.configuration().rate,
                       coordinator_.configuration().bpm, coordinator_.configuration().unit, cycle);
    std::uint64_t cycleFrames{};
    scheduler::round(cycle, cycleFrames);
    progress.completedCycles = cycleFrames == 0 ? 0 : frames / cycleFrames;
    progress.cursorFrames = cycleFrames == 0 ? 0 : frames % cycleFrames;
    progress.state = practice::State::Ended;
    progress.terminal = true;
    progress.partial = progress.cursorFrames != 0;
    progress.requestedStopNs = 1;
    return progress;
}

void FreeplayView::beginPersistence() {
    if (!store_ || persistencePending_ || persistenceBlocked_ || persistenceSaved_
        || (capture_ && !capture_->canLeave(true))) {
        if (!store_)
            persistenceStatus_ = "Freeplay stopped. No local Store is configured for this detached view; no local Freeplay history was saved.";
        return;
    }
    try {
        capture::StartRequest request;
        if (!freeplayConfiguration(request)) {
            persistenceStatus_ = "Freeplay stopped. Local Store binding is unavailable.";
            return;
        }
        capture_ = std::make_unique<capture::PracticeSession>(*store_, coordinator_);
        request.epoch = 1;
        if (!capture_->start(std::move(request), ++commandSequence_, monotonicMilliseconds())) {
            capture_.reset();
            persistenceStatus_ = "Freeplay history allocation was refused; no result was claimed.";
            return;
        }
        persistedNanoseconds_ = accumulatedNanoseconds_;
        persistencePending_ = true;
        persistenceSaved_ = false;
        persistenceStatus_ = "Saving Freeplay activity locally…";
    } catch (const std::exception& error) {
        persistenceStatus_ = std::string("Freeplay history could not start: ") + error.what();
        capture_.reset();
    }
}

void FreeplayView::servicePersistence() {
    if (!persistencePending_ || !capture_ || !utcNow_)
        return;
    try {
        const auto now = monotonicMilliseconds();
        capture_->poll(now, utcNow_());
        if (!exitDiscard_ && capture_->phase() == capture::SessionPhase::Ready) {
            if (!capture_->takeStart(now))
                throw std::runtime_error("Freeplay initial checkpoint did not release the stopped record");
            if (!coordinator_.progress(freeplayProgress(stoppedFrames())))
                throw std::runtime_error("Freeplay stopped facts were refused by the existing coordinator");
        }
        if (!exitDiscard_ && capture_->phase() == capture::SessionPhase::Review) {
            if (coordinator_.activeFrames() != stoppedFrames())
                throw std::runtime_error("Freeplay stopped duration is not bound to the original allocation. Keep this profile and use the existing recovery path; no zero-duration history was saved");
            if (!capture_->save(nullptr, capture::Outcome::Stop, now))
                throw std::runtime_error("Freeplay stopped record could not be sealed");
        }
        capture_->poll(now, utcNow_());
        if (capture_->phase() == capture::SessionPhase::Saved && capture_->canLeave(true)) {
            persistencePending_ = false;
            persistenceSaved_ = true;
            ++historyWrites_;
            persistenceStatus_ = "Freeplay activity saved locally. Back is safe now; Open Progress reviews this finalized Freeplay record read-only, and rhythm tools can be opened safely. It remains separate from curriculum progression. Choose Start new freeplay for a fresh activity with zero active time.";
        } else if (capture_->phase() == capture::SessionPhase::Failed
                   || capture_->phase() == capture::SessionPhase::AllocationUnknown) {
            persistencePending_ = false;
            persistenceBlocked_ = !capture_->canLeave(true);
            persistenceStatus_ = (capture_->feedback().code=="ALLOCATION_REFUSED_PRIOR_ACTIVITY"||capture_->feedback().code=="ALLOCATION_REFUSED_STORE_UNCERTAIN")&&capture_->canLeave(true)
                ? "This Freeplay activity was not saved or allocated because an earlier activity needs recovery. Return to Home. Keep this profile and its original recovery records; this profile needs recovery before a new activity can be saved."
                : capture_->phase() == capture::SessionPhase::AllocationUnknown
                ? "Freeplay history allocation is unresolved. The stopped active time is retained; this view cannot safely bind it through allocation inspection. Keep this profile and use the existing recovery path. No history was confirmed."
                : "Freeplay history is unresolved; the original local operation was retained. Choose Retry history save while remaining stopped; a new activity cannot replace unresolved ownership.";
        }
    } catch (const std::exception& error) {
        persistencePending_ = false;
        persistenceBlocked_ = !capture_->canLeave(true);
        persistenceStatus_ = std::string("Freeplay history is unresolved; original operation retained: ") + error.what();
    }
    if (!persistenceStatus_.empty())
        setStatus(persistenceStatus_, juce::dontSendNotification);
    refresh();
}

void FreeplayView::refresh() {
    timer_.setText(formatDuration(activeNanoseconds()), juce::dontSendNotification);
    profileState_.setVisible(store_ == nullptr && !persistenceSaved_);
    const bool resumeReady = paused_ && !stopped_;
    startButton.setButtonText(resumeReady ? "Resume freeplay" : stopped_ ? "Start new freeplay" : "Start freeplay");
    startButton.setTitle(resumeReady ? "Resume Freeplay and continue active-time capture without saving history"
        : stopped_ ? "Start a new Freeplay activity with zero active time; the previous activity is not resumed"
        : "Start Freeplay and begin active-time capture");
    startButton.setEnabled(!running_ && !persistencePending_ && !persistenceBlocked_
        && (!capture_ || capture_->canLeave(true)) && !coordinator_.pending());
    pauseButton.setEnabled(running_);
    stopButton.setEnabled(!stopped_ && !persistencePending_ && !persistenceBlocked_ && (running_ || paused_));
    retryButton.setVisible(stopped_ && store_ && !persistenceSaved_ && !persistencePending_);
    retryButton.setEnabled(retrySaveAvailable());
    retryButton.setExplicitFocusOrder(4);
    int navigationOrder = retryButton.isVisible() ? 5 : 4;
    for (auto* button : {&rhythmButton, &progressButton, &audioButton, &backButton})
        button->setExplicitFocusOrder(navigationOrder++);
    rhythmButton.setEnabled(!running_ && !persistencePending_ && !persistenceBlocked_);
    progressButton.setButtonText(persistenceSaved_ ? "Review Progress (read-only)" : "Open Progress");
    progressButton.setTitle(persistenceSaved_
        ? "Review saved Freeplay history in read-only Progress; no new activity or history is created."
        : "Open read-only Progress; Freeplay history is not saved until Stop completes.");
    progressButton.setEnabled(!running_ && !persistencePending_ && !persistenceBlocked_);
    audioButton.setEnabled(!running_ && !persistencePending_ && !persistenceBlocked_);
    backButton.setEnabled(!running_ && !persistencePending_ && !persistenceBlocked_);
    backButton.setButtonText("Back to "+juce::String::fromUTF8(returnDestination_.c_str()));
    backButton.setTitle(backButton.getButtonText()+(paused_?"; paused Freeplay time remains retained and unsaved. Return to Freeplay to Resume or Stop and save.":" after the original Freeplay history operation resolves."));
    retryButton.setButtonText("Check original history save");
    retryButton.setTitle("Check the retained original Freeplay history operation; keep the same owner and stopped active time, never start a replacement activity.");
}

void FreeplayView::paint(juce::Graphics& graphics) {
    graphics.fillAll(appearance::colour(0xff10212c));
    graphics.setColour(appearance::colour(0xff6bd5cb));
    if (getWidth() < 800)
        graphics.fillRect(24, 60, getWidth() - 48, 2);
    else
        graphics.fillRect(40, 116, getWidth() - 80, 2);
}

void FreeplayView::resized() {
    const auto width = getWidth() - 80;
    if (getWidth() < 800) {
        const auto compactWidth = std::max(1, getWidth() - 48);
        if (heading.getText().startsWith("FREEPLAY")
            && heading.getText().contains("SEPARATE LOCAL ACTIVITY"))
            heading.setText(juce::String::fromUTF8("Freeplay — Separate local activity"), juce::dontSendNotification);
        heading.setBounds(24, 16, compactWidth, 42);
        explanation.setBounds(24, 66, compactWidth, 112);
        timerCaption.setBounds(24, 188, compactWidth, 24);
        timer_.setBounds(24, 214, compactWidth, 46);
        status_.setBounds(24, 268, compactWidth, 110);
        profileState_.setBounds(24, 380, compactWidth, 24);
        startButton.setBounds(24, 410, 138, 36);
        pauseButton.setBounds(170, 410, 138, 36);
        stopButton.setBounds(316, 410, 138, 36);
        rhythmButton.setBounds(462, 410, 154, 36);
        progressButton.setBounds(24, 464, 140, 36);
        audioButton.setBounds(172, 464, 140, 36);
        backButton.setBounds(320, 464, 140, 36);
        retryButton.setBounds(24, 518, 180, 36);
        return;
    }
    if (heading.getText().startsWith("Freeplay")
        && heading.getText().contains("Separate local activity"))
        heading.setText(juce::String::fromUTF8("FREEPLAY — SEPARATE LOCAL ACTIVITY"), juce::dontSendNotification);
    heading.setBounds(40, 30, width, 48);
    explanation.setBounds(40, 135, width, 104);
    timerCaption.setBounds(40, 257, width, 24);
    timer_.setBounds(40, 282, width, 50);
    status_.setBounds(40, 340, width, 104);
    profileState_.setBounds(40, 446, width, 24);
    startButton.setBounds(40, 478, 180, 36);
    pauseButton.setBounds(230, 478, 180, 36);
    stopButton.setBounds(420, 478, 180, 36);
    retryButton.setBounds(610, 478, 230, 36);
    rhythmButton.setBounds(40, 532, 230, 36);
    progressButton.setBounds(280, 532, 180, 36);
    audioButton.setBounds(470, 532, 180, 36);
    backButton.setBounds(getWidth() - 220, 532, 180, 36);
}

}
