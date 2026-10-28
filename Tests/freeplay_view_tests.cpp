#include "desktop/FreeplayView.hpp"
#include "platform/ProfileAccessMac.hpp"

#include <juce_gui_basics/juce_gui_basics.h>

#include <filesystem>
#include <atomic>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

using fathom::desktop::FreeplayView;
using namespace fathom;

int main(int argc, char** argv) {
    if ((argc != 2 && argc != 3) || !std::filesystem::path(argv[1]).is_absolute() || std::filesystem::exists(argv[1]))
        return 2;

    const std::filesystem::path evidence = argv[1];
    std::filesystem::create_directories(evidence);
    std::ofstream checks(evidence / "checks.tsv");
    int count{};
    auto check = [&](const bool passed, const std::string& name) {
        ++count;
        checks << name << '\t' << (passed ? "PASS" : "FAIL") << '\n';
        checks.flush();
        if (!passed)
            throw std::runtime_error(name);
    };

    try {
        juce::ScopedJuceInitialiser_GUI gui;
        if(argc==3&&std::string(argv[2])=="--exit-discard-regression"){
            std::filesystem::permissions(evidence,std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);
            storage::StoreOptions options;options.path=evidence/"profile.sqlite";options.create=true;options.createdUtc="2026-10-10T00:00:00Z";storage::ProfileStore store(options);
            const auto before=store.snapshot(storage::newUuid()).get();check(before.status==storage::Status::Confirmed,"actual Freeplay baseline acknowledged");
            FreeplayView view;std::uint64_t tick=0;view.setClockForTest([&]{return tick;});check(view.configureStore(store,[]{return std::string("2026-10-10T00:00:10Z");},"Etc/UTC")&&view.startFreeplay(),"actual volatile Freeplay starts without peer");tick=2'000'000'000;
            view.cancelExit();check(view.active()&&view.historyWriteCount()==0,"Cancel does not stop or save volatile Freeplay");
            check(view.requestExit(true)&&!view.active()&&view.historyWriteCount()==0&&!view.persistencePending()&&!view.persistenceSaved(),"Discard stops volatile Freeplay without hidden history save");
            check(view.requestExit(true)&&view.historyWriteCount()==0,"repeated Freeplay Discard creates no persistence");
            const auto after=store.snapshot(storage::newUuid()).get();check(after.status==storage::Status::Confirmed&&after.data==before.data,"Freeplay Discard leaves all profile authority unchanged");return 0;
        }
        if (argc == 3 && std::string(argv[2]) == "--action-keys") {
            std::ofstream trace(evidence / "action-keys.tsv");
            trace << "width\taction\tkey\tactive\tback_calls\thistory_writes\n";
            desktop::ActionButton guard{"Guard"};
            int guardClicks = 0;
            guard.onClick = [&] { ++guardClicks; };
            guard.setEnabled(false);
            check(guard.keyPressed(juce::KeyPress{juce::KeyPress::spaceKey}) && guardClicks == 0,
                  "shared action button blocks disabled Space callback");
            guard.setEnabled(true);
            check(guard.keyPressed(juce::KeyPress{juce::KeyPress::returnKey}) && guardClicks == 1,
                  "shared action button invokes enabled Return callback synchronously once");
            for (const int width : {640, 920}) {
                FreeplayView view;
                view.setSize(width, 680);
                view.addToDesktop(juce::ComponentPeer::windowHasTitleBar);
                view.setVisible(true);
                auto* peer = view.getPeer();
                check(peer && view.isShowing(), "Freeplay visible desktop peer at " + std::to_string(width));
                auto* start = dynamic_cast<juce::TextButton*>(view.findChildWithID("freeplay-start"));
                auto* stop = dynamic_cast<juce::TextButton*>(view.findChildWithID("freeplay-stop"));
                auto* back = dynamic_cast<juce::TextButton*>(view.findChildWithID("freeplay-back"));
                check(start && stop && back && start->isShowing() && back->isShowing(),
                      "Freeplay actual Start, Stop and Back controls exist at " + std::to_string(width));
                int backCalls = 0;
                view.onBack = [&] { ++backCalls; };
                check(start->isEnabled() && !view.active() && view.historyWriteCount() == 0,
                      "Freeplay starts stopped without saved history at " + std::to_string(width));
                start->grabKeyboardFocus();
                check(juce::Component::getCurrentlyFocusedComponent() == start,
                      "Freeplay visible Start receives focus at " + std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),
                      "Freeplay focused Start consumes Space at " + std::to_string(width));
                check(view.active() && view.historyWriteCount() == 0,
                      "Freeplay Start Space begins one unsaved active interval at " + std::to_string(width));
                trace << width << "\tStart\tSpace\t1\t" << backCalls << '\t' << view.historyWriteCount() << '\n';
                check(stop->isShowing() && stop->isEnabled(), "Freeplay Stop becomes enabled at " + std::to_string(width));
                stop->grabKeyboardFocus();
                check(juce::Component::getCurrentlyFocusedComponent() == stop,
                      "Freeplay visible Stop receives focus at " + std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::returnKey}),
                      "Freeplay focused Stop consumes Return at " + std::to_string(width));
                check(!view.active() && view.canLeave() && view.historyWriteCount() == 0,
                      "Freeplay Stop Return leaves detached history unsaved at " + std::to_string(width));
                trace << width << "\tStop\tReturn\t0\t" << backCalls << '\t' << view.historyWriteCount() << '\n';
                back->grabKeyboardFocus();
                check(juce::Component::getCurrentlyFocusedComponent() == back,
                      "Freeplay visible Back receives focus at " + std::to_string(width));
                check(peer->handleKeyPress(juce::KeyPress{juce::KeyPress::spaceKey}),
                      "Freeplay focused Back consumes Space at " + std::to_string(width));
                check(backCalls == 1 && !view.active() && view.historyWriteCount() == 0,
                      "Freeplay Back Space returns once without saved history at " + std::to_string(width));
                trace << width << "\tBack\tSpace\t0\t" << backCalls << '\t' << view.historyWriteCount() << '\n';
                auto image = view.createComponentSnapshot(view.getLocalBounds());
                juce::FileOutputStream file{juce::File((evidence / ("freeplay-action-" + std::to_string(width) + ".png")).string())};
                juce::PNGImageFormat png;
                check(file.openedOk() && png.writeImageToStream(image, file),
                      "Freeplay action screenshot at " + std::to_string(width));
                view.removeFromDesktop();
            }
            trace.flush();
            check(trace.good(), "Freeplay action trace flushed");
            std::ofstream(evidence / "summary.json") << "{\"checks\":" << count << ",\"status\":\"PASS\",\"physicalKeyboard\":false,\"historyWrites\":0}\n";
            std::cout << "PASS " << count << " Freeplay action keyboard checks\n";
            return 0;
        }
        if (argc == 3 && std::string(argv[2]) == "--accessibility-capture") {
            for (const int width : {640, 920}) {
                FreeplayView view;
                view.setSize(width, 680);
                view.setVisible(true);
                view.resized();
                const auto snapshot = view.createComponentSnapshot(view.getLocalBounds());
                juce::FileOutputStream file{juce::File((evidence / ("freeplay-" + std::to_string(width) + ".png")).string())};
                juce::PNGImageFormat png;
                check(file.openedOk() && png.writeImageToStream(snapshot, file),
                      "Freeplay native snapshot written at " + std::to_string(width));
                file.flush();
                check(!file.getStatus().failed(), "Freeplay native snapshot flushed at " + std::to_string(width));
                juce::KeyboardFocusTraverser traverser;
                std::ofstream focus(evidence / ("focus-" + std::to_string(width) + ".tsv"));
                const auto order = traverser.getAllComponents(&view);
                for (const auto* control : order)
                    focus << control->getComponentID() << '\t' << control->isEnabled() << '\t'
                          << control->getBounds().toString() << '\n';
                check(focus.good(), "Freeplay focus trace written at " + std::to_string(width));
                const char* enabledOrder[] = {"freeplay-start", "freeplay-rhythm-tools", "freeplay-open-progress", "freeplay-audio-settings", "freeplay-back"};
                bool ordered = order.size() == std::size(enabledOrder);
                for (std::size_t index = 0; index < order.size() && index < std::size(enabledOrder); ++index)
                    ordered = ordered && order[index]->getComponentID() == enabledOrder[index]
                        && order[index]->isEnabled()
                        && (index + 1 == order.size() || traverser.getNextComponent(order[index]) == order[index + 1]);
                check(ordered, "Freeplay enabled keyboard traversal follows visual action order at " + std::to_string(width));
                auto* explanation = dynamic_cast<juce::Label*>(view.findChildWithID("freeplay-explanation"));
                auto* status = dynamic_cast<juce::Label*>(view.findChildWithID("freeplay-status"));
                check(explanation && explanation->getText().length() < 280
                          && explanation->getText().contains("no lesson prerequisite")
                          && explanation->getText().contains("no curriculum credit")
                          && explanation->getHelpText().contains("--capture-preview <new private directory> <IANA timezone>"),
                      "Freeplay entry is concise with full guidance at " + std::to_string(width));
                check(status && status->getText().length() < 210
                          && status->getText().contains("Choose Start freeplay")
                          && status->getText().contains("configured profile")
                          && status->getHelpText() == juce::String{view.statusText()},
                      "Freeplay stopped state is concise with full accessible status at " + std::to_string(width));
            }
            std::ofstream(evidence / "summary.json") << "{\"checks\":" << count << ",\"status\":\"PASS\"}\n";
            std::cout << "PASS " << count << " Freeplay accessibility capture checks\n";
            return 0;
        }
        if (argc == 3 && std::string(argv[2]) == "--responsive-layout") {
            FreeplayView compact;
            compact.setSize(640, 680);
            compact.setVisible(true);
            compact.resized();
            const auto bounds = compact.getLocalBounds();
            const char* visibleIds[] = {"freeplay-explanation", "freeplay-status", "freeplay-profile-state", "freeplay-start", "freeplay-pause", "freeplay-stop", "freeplay-rhythm-tools", "freeplay-open-progress", "freeplay-audio-settings", "freeplay-back"};
            for (const auto* id : visibleIds) {
                const auto* component = compact.findChildWithID(id);
                check(component && component->isVisible() && bounds.contains(component->getBounds()) && component->getWidth() > 0 && component->getHeight() > 0,
                      std::string("Compact Freeplay surface remains visible and contained: ") + id);
            }
            const char* actions[] = {"freeplay-start", "freeplay-pause", "freeplay-stop", "freeplay-rhythm-tools", "freeplay-open-progress", "freeplay-audio-settings", "freeplay-back"};
            for (std::size_t leftIndex = 0; leftIndex < std::size(actions); ++leftIndex)
                for (std::size_t rightIndex = leftIndex + 1; rightIndex < std::size(actions); ++rightIndex) {
                    const auto* left = compact.findChildWithID(actions[leftIndex]);
                    const auto* right = compact.findChildWithID(actions[rightIndex]);
                    check(left && right && !left->getBounds().intersects(right->getBounds()),
                          std::string("Compact Freeplay actions do not overlap: ") + actions[leftIndex] + "/" + actions[rightIndex]);
                }
            const std::pair<const char*, const char*> labels[] = {{"freeplay-start", "Start freeplay"}, {"freeplay-pause", "Pause freeplay"}, {"freeplay-stop", "Stop freeplay"}, {"freeplay-rhythm-tools", "Open rhythm tools"}, {"freeplay-open-progress", "Open Progress"}, {"freeplay-audio-settings", "Audio settings"}, {"freeplay-back", "Back"}};
            for (const auto& expected : labels) {
                const auto* button = dynamic_cast<const juce::TextButton*>(compact.findChildWithID(expected.first));
                check(button && button->getButtonText().toStdString() == expected.second,
                      std::string("Compact Freeplay preserves label: ") + expected.first);
            }
            check(compact.findChildWithID("freeplay-explanation")
                      && dynamic_cast<const juce::Label*>(compact.findChildWithID("freeplay-explanation"))
                      && dynamic_cast<const juce::Label*>(compact.findChildWithID("freeplay-explanation"))->getText().isNotEmpty(),
                  "Compact Freeplay retains authored explanation while the heading is compact");
            const auto* compactHeading = dynamic_cast<const juce::Label*>(compact.getChildComponent(0));
            check(compactHeading && compactHeading->getText().startsWith("Freeplay")
                      && compactHeading->getText().contains("Separate local activity"),
                  "Compact Freeplay uses a readable identity heading");
            check(!compact.active() && compact.canLeave() && compact.activeNanoseconds() == 0 && compact.historyWriteCount() == 0,
                  "Compact Freeplay opens stopped with no local activity");
            FreeplayView standard;
            standard.setSize(920, 680);
            standard.setVisible(true);
            standard.resized();
            const auto* standardHeading = dynamic_cast<const juce::Label*>(standard.getChildComponent(0));
            check(standardHeading && standardHeading->getText().startsWith("FREEPLAY")
                      && standardHeading->getText().contains("SEPARATE LOCAL ACTIVITY"),
                  "Standard Freeplay restores the authored identity heading");
            check(standard.findChildWithID("freeplay-start")->getBounds().getX() == 40
                      && standard.findChildWithID("freeplay-start")->getBounds().getWidth() == 180
                      && standard.findChildWithID("freeplay-back")->getBounds().getX() == 700,
                  "Standard Freeplay geometry remains unchanged at 920x680");
            std::ofstream(evidence / "summary.json") << "{\"checks\":" << count << ",\"status\":\"PASS\",\"profileConfigured\":false,\"active\":false,\"historyWrites\":0}\n";
            std::cout << "PASS " << count << " Compact Freeplay responsive layout checks\n";
            return 0;
        }
        FreeplayView view;
        view.setSize(920, 680);
        view.setVisible(true);
        std::uint64_t now{};
        view.setClockForTest([&now] { return now; });
        const auto* explanation = dynamic_cast<const juce::Label*>(view.findChildWithID("freeplay-explanation"));
        const auto* startButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-start"));
        const auto* pauseButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-pause"));
        const auto* stopButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-stop"));
        const auto* rhythmButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-rhythm-tools"));
        const auto* progressButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-open-progress"));
        const auto* audioButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-audio-settings"));
        const auto* backButton = dynamic_cast<const juce::TextButton*>(view.findChildWithID("freeplay-back"));
        const auto* profileState = dynamic_cast<const juce::Label*>(view.findChildWithID("freeplay-profile-state"));
        auto startLabel = [&view] {
            for (auto* child : view.getChildren())
                if (const auto* button = dynamic_cast<const juce::TextButton*>(child))
                    if (button->getButtonText() == "Start freeplay" || button->getButtonText() == "Resume freeplay"
                        || button->getButtonText() == "Start new freeplay")
                        return button->getButtonText().toStdString();
            return std::string{};
        };
        FreeplayView zeroPause;
        std::uint64_t zeroPauseNow{};
        zeroPause.setClockForTest([&zeroPauseNow] { return zeroPauseNow; });
        check(zeroPause.startFreeplay() && zeroPause.pauseFreeplay()
                  && zeroPause.activeNanoseconds() == 0
                  && dynamic_cast<const juce::TextButton*>(zeroPause.findChildWithID("freeplay-start"))
                  && dynamic_cast<const juce::TextButton*>(zeroPause.findChildWithID("freeplay-start"))->getButtonText().toStdString() == "Resume freeplay"
                  && dynamic_cast<const juce::TextButton*>(zeroPause.findChildWithID("freeplay-start"))->getTitle().toStdString() == "Resume Freeplay and continue active-time capture without saving history",
              "zero-time Pause exposes Resume without adding active time");
        check(zeroPause.stopFreeplay() && !zeroPause.stopFreeplay() && !zeroPause.pauseFreeplay()
                  && zeroPause.activeNanoseconds() == 0 && zeroPause.historyWriteCount() == 0,
              "zero-time paused Stop is terminal and idempotent without claiming history");
        FreeplayView idleClose;
        check(idleClose.requestClose() && idleClose.requestClose()
                  && idleClose.closeState() == FreeplayView::CloseState::Ready
                  && idleClose.activeNanoseconds() == 0 && idleClose.historyWriteCount() == 0,
              "idle repeated Quit is ready without creating an activity or history");
        for (const bool paused : {false, true}) {
            FreeplayView detachedClose;
            std::uint64_t closeNow{};
            detachedClose.setClockForTest([&closeNow] { return closeNow; });
            check(detachedClose.startFreeplay(), "detached Quit fixture starts");
            closeNow = 2'000'000'000ULL;
            if (paused) {
                check(detachedClose.pauseFreeplay() && detachedClose.canLeave(),
                      "paused navigation retains its existing leave guard before Quit");
                closeNow = 7'000'000'000ULL;
            }
            check(detachedClose.requestClose() && !detachedClose.active()
                      && detachedClose.closeState() == FreeplayView::CloseState::Ready
                      && detachedClose.activeNanoseconds() == 2'000'000'000ULL
                      && detachedClose.historyWriteCount() == 0
                      && !detachedClose.stopFreeplay() && !detachedClose.pauseFreeplay()
                      && detachedClose.persistenceStatus().find("no local Freeplay history was saved") != std::string::npos,
                  paused ? "Quit terminalizes detached Pause without counting paused time or claiming history"
                         : "Quit terminalizes detached running time without claiming history");
            closeNow += 3'000'000'000ULL;
            check(detachedClose.requestClose() && detachedClose.activeNanoseconds() == 2'000'000'000ULL
                      && detachedClose.historyWriteCount() == 0,
                  "repeated detached Quit preserves the exact stopped interval");
        }
        FreeplayView disconnected;
        disconnected.setSize(920, 680);
        std::uint64_t disconnectedNow{};
        disconnected.setClockForTest([&disconnectedNow] { return disconnectedNow; });
        check(!disconnected.requestBack()
                  && disconnected.statusText().find("Back is unavailable from Freeplay until the existing Home route is connected") != std::string::npos
                  && disconnected.historyWriteCount() == 0 && disconnected.activeNanoseconds() == 0,
              "missing Freeplay Back route refuses silently successful leave and preserves state");
        check(!disconnected.requestProgress()
                  && disconnected.statusText().find("Progress is unavailable from Freeplay until the existing Progress page is connected") != std::string::npos
                  && disconnected.statusText().find("Return to Home and choose Progress") != std::string::npos
                  && disconnected.historyWriteCount() == 0 && disconnected.activeNanoseconds() == 0,
              "missing Freeplay Progress route gives Home recovery without mutation");
        check(!disconnected.requestRhythmTools()
                  && disconnected.statusText().find("Rhythm tools are unavailable from Freeplay until the existing rhythm-tools page is connected") != std::string::npos
                  && disconnected.statusText().find("choose Metronome or Rhythm preview") != std::string::npos
                  && disconnected.historyWriteCount() == 0 && disconnected.activeNanoseconds() == 0,
              "missing Freeplay rhythm route gives Home recovery without starting sound");
        check(!disconnected.requestAudioSettings()
                  && disconnected.statusText().find("Audio settings are unavailable from Freeplay until the existing shared Audio page is connected") != std::string::npos
                  && disconnected.statusText().find("choose Audio settings") != std::string::npos
                  && disconnected.historyWriteCount() == 0 && disconnected.activeNanoseconds() == 0,
              "missing Freeplay Audio route gives Home recovery without starting sound");
        int audioCalls{};
        view.onAudioSettings = [&audioCalls] { ++audioCalls; };
        view.setClockForTest([&now] { return now; });
        check(audioButton && audioButton->getButtonText().toStdString() == "Audio settings" && audioButton->isEnabled(),
              "stopped Freeplay exposes the shared Audio-settings handoff");
        check(view.requestAudioSettings() && audioCalls == 1,
              "stopped Freeplay opens shared Audio settings without mutation");
        check(progressButton && progressButton->getButtonText().toStdString() == "Open Progress" && progressButton->isEnabled(),
              "stopped Freeplay exposes an enabled Open Progress handoff");
        check(explanation
                  && explanation->getHelpText().toStdString().find("Start counts active time. Pause retains active time without recording history. Stop requests one separate local Freeplay history save when a local profile is configured; Back and rhythm tools wait until that save is confirmed.") != std::string::npos,
              "Freeplay accessible guidance states active-time, save and safe-exit boundaries");
        check(explanation->getHelpText().toStdString().find("Use Audio settings for shared speakers and headphones; open Audio settings without starting sound.") != std::string::npos,
              "Freeplay accessible guidance identifies shared Audio settings without auto-play");
        check(explanation->getHelpText().toStdString().find("Without a configured local profile, Start and Stop only demonstrate the timer") != std::string::npos
                  && explanation->getHelpText().toStdString().find("--capture-preview <new private directory> <IANA timezone>") != std::string::npos,
              "Freeplay accessible guidance identifies the profile-dependent Development Preview path without claiming saved history");
        check(profileState && profileState->isVisible()
                  && profileState->getText().toStdString() == "No local profile configured; Freeplay history stays unsaved."
                  && profileState->getTitle().toStdString() == "Freeplay local-profile boundary marker.",
              "Freeplay exposes the exact no-profile history boundary marker");
        check(startButton && pauseButton && stopButton && rhythmButton && progressButton && audioButton && backButton,
              "Freeplay exposes stable IDs for every transport and navigation control");
        bool actionPresentation = true;
        for (const auto* button : {startButton, pauseButton, stopButton, rhythmButton, progressButton, audioButton, backButton})
            actionPresentation = actionPresentation
                && button->findColour(juce::TextButton::buttonColourId) == juce::Colour{0xff6bd5cb}
                && button->findColour(juce::TextButton::textColourOffId) == juce::Colour{0xff10212c}
                && button->findColour(juce::TextButton::textColourOnId) == juce::Colour{0xff10212c};
        check(actionPresentation,
              "Freeplay action buttons use the primary presentation while preserving the existing control contract");
        const auto contained = [&view](const juce::Component* component) {
            return component && view.getLocalBounds().contains(component->getBounds());
        };
        check(view.findChildWithID("freeplay-status")
                  && view.findChildWithID("freeplay-status")->getBounds().getHeight() >= 104
                  && contained(view.findChildWithID("freeplay-status"))
                  && contained(profileState)
                  && contained(startButton) && contained(pauseButton) && contained(stopButton)
                  && contained(rhythmButton) && contained(progressButton) && contained(audioButton)
                  && contained(backButton)
                  && view.findChildWithID("freeplay-status")->getBottom() <= startButton->getY()
                  && profileState->getBottom() <= startButton->getY()
                  && stopButton->getBottom() <= rhythmButton->getY()
                  && rhythmButton->getBottom() <= view.getHeight(),
              "Freeplay status and action rows reserve readable contained non-overlapping space");
        check(startButton->getTitle() == "Start Freeplay and begin active-time capture"
                  && pauseButton->getTitle() == "Pause Freeplay and retain active time without saving history"
                  && stopButton->getTitle() == "Stop Freeplay and save one separate local history record when configured"
                  && rhythmButton->getTitle() == "Open rhythm tools after Freeplay is stopped"
                  && progressButton->getTitle() == "Open read-only Progress; Freeplay history is not saved until Stop completes."
                  && audioButton->getTitle() == "Open shared Audio settings without starting sound"
                  && backButton->getTitle() == "Return to Home after Freeplay is safely stopped",
              "Freeplay control titles state action and safe boundary");
        check(startButton->getWantsKeyboardFocus() && rhythmButton->getWantsKeyboardFocus()
                  && progressButton->getWantsKeyboardFocus() && audioButton->getWantsKeyboardFocus()
                  && backButton->getWantsKeyboardFocus()
                  && startButton->getExplicitFocusOrder() == 1 && pauseButton->getExplicitFocusOrder() == 2
                  && stopButton->getExplicitFocusOrder() == 3 && rhythmButton->getExplicitFocusOrder() == 4
                  && progressButton->getExplicitFocusOrder() == 5 && audioButton->getExplicitFocusOrder() == 6
                  && backButton->getExplicitFocusOrder() == 7,
              "Freeplay controls expose deterministic keyboard focus order");

        check(!view.active() && view.canLeave() && view.activeNanoseconds() == 0, "initial stopped with zero active time");
        check(startLabel() == "Start freeplay", "initial Freeplay exposes the Start action");
        check(view.historyWriteCount() == 0
                  && view.statusText().find("Freeplay is stopped; Opening Freeplay does not start sound. Back is safe now, and this view has no new local history until Start and Stop are completed.") != std::string::npos
                  && view.statusText().find("No activity has been recorded yet. Stop saves one local Freeplay history entry when a local profile is configured; Freeplay never grants curriculum progress.") != std::string::npos
                  && view.statusText().find("Open Progress after the save is confirmed to review the finalized Freeplay record read-only.") != std::string::npos
                  && view.statusText().find("Next action: choose Start freeplay to begin active-time capture; Stop saves one separate local Freeplay history entry when a local profile is configured.") != std::string::npos,
              "standalone context states safe Back, profile-dependent local history, read-only Progress and the explicit Start next action");

        check(view.startFreeplay(), "Start command accepted");
        check(view.active() && !view.canLeave(), "explicit start enters active Freeplay");
        check(pauseButton->getWantsKeyboardFocus() && stopButton->getWantsKeyboardFocus(),
              "active Freeplay exposes keyboard-focusable Pause and Stop controls");
    check(view.statusText().find("Freeplay timer running. Stop is required to create one separate local history record; Freeplay never grants curriculum progress.") != std::string::npos
              && view.statusText().find("Pause retains active time without recording history.") != std::string::npos,
          "active Freeplay states the explicit save boundary and no-curriculum contract");
        check(!view.requestAudioSettings() && audioCalls == 1
                  && view.statusText().find("Pause or stop Freeplay before opening Audio settings") != std::string::npos,
              "active Freeplay blocks Audio settings with actionable guidance");
        now = 2'000'000'000ULL;
        check(view.activeNanoseconds() == 2'000'000'000ULL, "active timer advances from injected monotonic clock");
        check(view.pauseFreeplay(), "Pause command accepted");
        check(!view.presentationStoppedAndResolved(), "Paused Freeplay permits safe navigation but remains ineligible for stopped-and-resolved settings save");
        check(!view.active() && view.canLeave() && view.activeNanoseconds() == 2'000'000'000ULL && view.timerText() == "00:00:02",
              "pause retains active time");
        check(startLabel() == "Resume freeplay", "paused Freeplay exposes the Resume action");
        check(view.statusText().find("Freeplay paused. Active time retained; inactive time is not counted. Stop remains required to create one separate local history record; Back is safe while paused.") != std::string::npos
                  && view.statusText().find("Resume continues active time without recording history.") != std::string::npos,
              "paused Freeplay states retained time, save boundary and safe Back");
        now = 7'000'000'000ULL;
        check(view.activeNanoseconds() == 2'000'000'000ULL, "paused interval is excluded");

        int backCalls{};
        view.onBack = [&backCalls] { ++backCalls; };
        check(view.startFreeplay(), "second Start command accepted");
        now = 9'000'000'000ULL;
        check(!view.requestBack(), "active Back command refused");
        check(view.active() && backCalls == 0 && view.statusText().find("Pause or stop") != std::string::npos,
              "Back refuses while active with actionable guidance");
        check(view.stopFreeplay(), "Stop command accepted");
        check(!view.active() && view.activeNanoseconds() == 4'000'000'000ULL && view.historyWriteCount() == 0,
              "stop retains active time without creating history");
        check(view.statusText().find("No local Store is configured for this detached view; no local Freeplay history was saved.") != std::string::npos,
              "detached Stop explicitly reports that no local Freeplay history was saved");
        check(startLabel() == "Start new freeplay" && !stopButton->isEnabled()
                  && !view.stopFreeplay() && !view.pauseFreeplay() && !view.retryPersistence()
                  && view.activeNanoseconds() == 4'000'000'000ULL,
              "detached Stop retains its terminal duration with no Resume or duplicate Stop");
        check(view.requestBack(), "Back command accepted after stop");
        check(backCalls == 1, "Back succeeds after stop");

        int progressCalls{};
        view.onProgress = [&progressCalls] { ++progressCalls; };
        check(view.requestProgress() && progressCalls == 1, "stopped Freeplay opens read-only Progress without mutation");

        int rhythmCalls{};
        view.onRhythmTools = [&rhythmCalls] { ++rhythmCalls; };
        check(view.requestRhythmTools(), "Open rhythm tools command accepted");
        check(rhythmCalls == 1 && !view.active(), "rhythm tools require explicit stopped action");

        check(view.startFreeplay(), "third Start command accepted");
        check(view.activeNanoseconds() == 0 && view.timerText() == "00:00:00",
              "explicit new detached Start clears only the previous stopped duration");
        check(!view.startFreeplay() && view.active(), "repeated start preserves active state");
        check(!view.requestProgress() && progressCalls == 1 && view.statusText().find("Pause or stop Freeplay before opening Progress") != std::string::npos,
              "active Freeplay blocks Progress handoff with actionable guidance");
        check(!view.requestRhythmTools() && rhythmCalls == 1
                  && view.statusText().find("Pause or stop Freeplay before opening rhythm tools") != std::string::npos,
              "active Freeplay blocks Rhythm-tools handoff with actionable guidance");
        check(view.pauseFreeplay(), "pause command is accepted from active state");
        check(!view.pauseFreeplay(), "repeated pause preserves stopped state");
        check(view.activeNanoseconds() == 0, "repeated controls preserve the fresh activity time");

        const auto configuredDirectory = evidence / "configured-profile";
        std::filesystem::create_directories(configuredDirectory);
        std::filesystem::permissions(configuredDirectory, std::filesystem::perms::owner_all, std::filesystem::perm_options::replace);
        storage::StoreOptions options;
        options.path = configuredDirectory / "profile.sqlite";
        options.create = true;
        options.createdUtc = "2026-09-13T18:08:00Z";
        std::atomic<int> saveFault{};
        std::atomic<bool> closeGate{}, closeGateEntered{};
        options.diagnosticHook = [&](const std::string& phase, const std::string& operation) {
            if (closeGate && phase == "before_operation" && operation.find(".allocate") != std::string::npos) {
                closeGateEntered = true;
                while (closeGate)
                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
            const auto mode = saveFault.load();
            const bool allocationFailure = mode == 1 && operation.find(".allocate") != std::string::npos
                && phase == "before_operation";
            const bool saveFailure = (mode == 2 || mode == 3) && operation.find(".save.commit") != std::string::npos
                && phase == (mode == 2 ? "before_commit" : "after_commit");
            if ((allocationFailure || saveFailure) && saveFault.exchange(0) == mode)
                throw std::runtime_error("Controlled Freeplay allocation/save failure or lost receipt");
        };
        storage::ProfileStore store(options);
        struct GateRelease {
            std::atomic<bool>& gate;
            ~GateRelease() { gate = false; }
        } gateRelease{closeGate};
        FreeplayView closeBeforeAllocationError;
        std::uint64_t errorCloseNow{};
        bool failCloseStamp{};
        closeBeforeAllocationError.setClockForTest([&errorCloseNow] { return errorCloseNow; });
        check(closeBeforeAllocationError.configureStore(store, [&failCloseStamp] {
                  if (failCloseStamp)
                      throw std::runtime_error("Controlled Freeplay UTC unavailable");
                  return std::string("2026-09-13T18:08:30Z");
              }, "America/New_York") && closeBeforeAllocationError.startFreeplay(),
              "preallocation Quit error fixture binds and starts normally");
        errorCloseNow = 2'000'000'000ULL;
        failCloseStamp = true;
        check(!closeBeforeAllocationError.requestClose()
                  && closeBeforeAllocationError.closeState() == FreeplayView::CloseState::Blocked
                  && closeBeforeAllocationError.canLeave()
                  && closeBeforeAllocationError.activeNanoseconds() == 2'000'000'000ULL
                  && closeBeforeAllocationError.persistenceStatus().find("Controlled Freeplay UTC unavailable") != std::string::npos,
              "failure before allocating history holds Quit despite the clear navigation guard");
        const auto allocationStartError = closeBeforeAllocationError.persistenceStatus();
        check(!closeBeforeAllocationError.requestClose() && !closeBeforeAllocationError.persistencePending()
                  && closeBeforeAllocationError.persistenceStatus() == allocationStartError
                  && closeBeforeAllocationError.historyWriteCount() == 0,
              "repeated preallocation-error Quit preserves the exact stopped duration and error without retry");
        FreeplayView persisted;
        persisted.setSize(920, 680);
        std::uint64_t persistedNow{};
        persisted.setClockForTest([&persistedNow] { return persistedNow; });
        check(persisted.configureStore(store, [] { return std::string("2026-09-13T18:08:30Z"); }, "America/New_York"),
              "configured Freeplay binds existing local Store");
        check(!dynamic_cast<const juce::Label*>(persisted.findChildWithID("freeplay-profile-state"))->isVisible(),
              "configured Freeplay hides the no-profile history boundary marker");
        check(storage::ProfileStore::schemaIdentity().size() == 64, "configured Freeplay retains pinned schema identity");
        check(persisted.startFreeplay(), "configured Freeplay starts explicitly");
        persistedNow = 1'000'000'000ULL;
        check(persisted.pauseFreeplay(), "configured Freeplay pauses without persistence");
        auto beforePauseFuture = store.snapshot("configured-before-pause");
        check(storage::ProfileStore::waitForAcknowledgment(beforePauseFuture).status == storage::Status::Confirmed,
              "pause snapshot is available");
        persistedNow = 3'000'000'000ULL;
        closeGate = true;
        const auto closeBegan = std::chrono::steady_clock::now();
        const bool closedPaused = persisted.requestClose();
        check(!closedPaused && std::chrono::steady_clock::now() - closeBegan < std::chrono::seconds(1)
                  && persisted.closeState() == FreeplayView::CloseState::Pending,
              "configured paused Quit returns promptly while the original allocation worker is blocked");
        for (int attempt = 0; attempt < 1000 && !closeGateEntered; ++attempt)
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        check(closeGateEntered && !persisted.requestClose() && !persisted.requestClose()
                  && persisted.activeNanoseconds() == 1'000'000'000ULL && persisted.historyWriteCount() == 0,
              "repeated pending Quit retains exactly the original paused duration without waiting or replacing allocation");
        closeGate = false;
        check(persisted.persistencePending() && !persisted.canLeave(), "Stop enters pending local history save");
        check(!persisted.startFreeplay() && !persisted.stopFreeplay() && !persisted.pauseFreeplay()
                  && !persisted.retryPersistence()
                  && !persisted.configureStore(store, [] { return std::string("2026-09-13T18:08:30Z"); }, "America/New_York")
                  && persisted.activeNanoseconds() == 1'000'000'000ULL,
              "pending save rejects direct transport retry and profile rebinding without changing stopped time");
        int pendingProgressCalls{};
        persisted.onProgress = [&pendingProgressCalls] { ++pendingProgressCalls; };
        check(!persisted.requestProgress() && pendingProgressCalls == 0
                  && persisted.statusText().find("still being saved locally") != std::string::npos,
              "pending Freeplay save blocks Progress handoff with actionable guidance");
        int pendingRhythmCalls{};
        persisted.onRhythmTools = [&pendingRhythmCalls] { ++pendingRhythmCalls; };
        check(!persisted.requestRhythmTools() && pendingRhythmCalls == 0
                  && persisted.statusText().find("still being saved locally") != std::string::npos,
              "pending Freeplay save blocks Rhythm tools with actionable guidance");
        for (int attempt = 0; attempt < 4000 && !persisted.persistenceSaved(); ++attempt) {
            persisted.servicePersistence();
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        check(persisted.persistenceSaved() && persisted.historyWriteCount() == 1 && persisted.canLeave()
                  && persisted.persistenceStatus().find("saved locally") != std::string::npos
                  && persisted.persistenceStatus().find("Freeplay activity saved locally. Back is safe now; Open Progress reviews this finalized Freeplay record read-only, and rhythm tools can be opened safely. It remains separate from curriculum progression.") != std::string::npos,
              "configured Freeplay confirms one local activity record (" + persisted.persistenceStatus() + ")");
        check(persisted.requestClose() && persisted.requestClose()
                  && persisted.closeState() == FreeplayView::CloseState::Ready
                  && persisted.historyWriteCount() == 1,
              "Quit becomes ready only after the original paused history save is confirmed");
        auto* persistedProgress = dynamic_cast<const juce::TextButton*>(persisted.findChildWithID("freeplay-open-progress"));
        check(persistedProgress && persistedProgress->isEnabled() && persistedProgress->getButtonText() == "Review Progress (read-only)",
              "confirmed Freeplay history exposes the read-only Progress action");
        check(persisted.requestProgress() && pendingProgressCalls == 1,
              "confirmed Freeplay save restores the stopped Progress handoff");
        check(persisted.requestRhythmTools() && pendingRhythmCalls == 1,
              "confirmed Freeplay save restores the stopped Rhythm-tools route");
        const auto* savedStart = dynamic_cast<const juce::TextButton*>(persisted.findChildWithID("freeplay-start"));
        const auto* savedStop = dynamic_cast<const juce::TextButton*>(persisted.findChildWithID("freeplay-stop"));
        check(savedStart && savedStart->isEnabled() && savedStart->getButtonText() == "Start new freeplay"
                  && savedStop && !savedStop->isEnabled()
                  && !persisted.stopFreeplay() && !persisted.pauseFreeplay() && !persisted.retryPersistence(),
              "Saved exposes explicit fresh Start and refuses duplicate Stop Pause and retry");
        auto configuredFuture = store.snapshot("configured-after-stop");
        const auto configured = storage::ProfileStore::waitForAcknowledgment(configuredFuture);
        const auto& configuredAuthority = configured.data.object().at("authoritative");
        check(configuredAuthority.object().at("identity").array().size() == 1
                  && configuredAuthority.object().at("finalized").array().size() == 1
                  && configuredAuthority.object().at("session").array().empty()
                  && configuredAuthority.object().at("finalized").array().front().array().at(7) == json::Value("1")
                  && configuredAuthority.object().at("finalized").array().front().array().at(8) == json::Value("1"),
              "configured paused Stop finalizes exactly one second of Freeplay without a Session");
        for (int attempt = 0; attempt < 8; ++attempt) {
            check(!persisted.stopFreeplay(), "repeated terminal Stop creates no new operation " + std::to_string(attempt));
            persisted.servicePersistence();
        }
        auto repeatedFuture = store.snapshot("configured-after-repeated-stop");
        const auto repeated = storage::ProfileStore::waitForAcknowledgment(repeatedFuture);
        check(repeated.status == storage::Status::Confirmed
                  && repeated.data.object().at("authoritative") == configuredAuthority
                  && persisted.historyWriteCount() == 1,
              "repeated terminal commands preserve exact authoritative history");
        check(persisted.startFreeplay() && !persisted.persistenceSaved()
                  && persisted.activeNanoseconds() == 0 && persisted.timerText() == "00:00:00",
              "explicit new configured Start resets duration and re-arms released capture ownership");
        persistedNow = 5'000'000'000ULL;
        check(!persisted.requestClose() && !persisted.active()
                  && persisted.closeState() == FreeplayView::CloseState::Pending
                  && persisted.activeNanoseconds() == 2'000'000'000ULL,
              "configured running Quit stops exactly the fresh active interval and awaits its history");
        for (int attempt = 0; attempt < 4000 && !persisted.persistenceSaved(); ++attempt) {
            persisted.servicePersistence();
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        auto freshFuture = store.snapshot("configured-fresh-activity");
        const auto fresh = storage::ProfileStore::waitForAcknowledgment(freshFuture);
        const auto& freshAuthority = fresh.data.object().at("authoritative");
        check(persisted.persistenceSaved() && persisted.historyWriteCount() == 2
                  && persisted.activeNanoseconds() == 2'000'000'000ULL
                  && freshAuthority.object().at("identity").array().size() == 2
                  && freshAuthority.object().at("finalized").array().size() == 2
                  && freshAuthority.object().at("session").array().empty(),
              "fresh activity saves a second original with only its own active time and no lesson Session");
        check(persisted.requestClose() && persisted.historyWriteCount() == 2,
              "running Quit releases after one new original is confirmed without an extra history write");
        for (const auto& original : configuredAuthority.object().at("finalized").array()) {
            bool retained = false;
            for (const auto& row : freshAuthority.object().at("finalized").array())
                retained = retained || row == original;
            check(retained, "fresh activity preserves the previous finalized original exactly");
        }
        bool freshDuration = false;
        for (const auto& row : freshAuthority.object().at("finalized").array())
            freshDuration = freshDuration || (row.array().at(7) == json::Value("2")
                && row.array().at(8) == json::Value("1"));
        check(freshDuration, "fresh original contains exactly two seconds rather than the prior accumulated duration");

        for (const int mode : {1, 2, 3}) {
            FreeplayView retryView;
            retryView.setSize(920, 680);
            std::uint64_t retryNow{};
            retryView.setClockForTest([&retryNow] { return retryNow; });
            check(retryView.configureStore(store, [] { return std::string("2026-09-13T18:08:30Z"); }, "America/New_York")
                      && retryView.startFreeplay(),
                  "fault fixture binds and starts a fresh Freeplay activity " + std::to_string(mode));
            retryNow = 2'000'000'000ULL;
            saveFault = mode;
            check(retryView.pauseFreeplay() && retryView.stopFreeplay(),
                  "fault fixture explicitly stops paused Freeplay " + std::to_string(mode));
            for (int attempt = 0; attempt < 4000 && retryView.persistencePending(); ++attempt) {
                retryView.servicePersistence();
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
            const auto* retry = dynamic_cast<const juce::TextButton*>(retryView.findChildWithID("freeplay-retry-save"));
            check(!retryView.persistencePending() && !retryView.persistenceSaved() && saveFault == 0
                      && retry && retry->isVisible() && retry->isEnabled()
                      && retry->getExplicitFocusOrder() == 4
                      && retryView.getLocalBounds().contains(retry->getBounds())
                      && !retryView.stopFreeplay() && !retryView.pauseFreeplay(),
                  "failed or lost receipt retains stopped activity and exposes explicit retry " + std::to_string(mode));
            if (mode != 1)
                check(!retryView.canLeave() && !retryView.startFreeplay()
                          && !retryView.configureStore(store, [] { return std::string("2026-09-13T18:08:30Z"); }, "America/New_York"),
                      "failed or lost final receipt blocks replacement and profile rebinding " + std::to_string(mode));
            auto beforeRetryFuture = store.snapshot("fault-before-retry-" + std::to_string(mode));
            const auto beforeRetry = storage::ProfileStore::waitForAcknowledgment(beforeRetryFuture);
            check(beforeRetry.status == storage::Status::Confirmed, "fault snapshot readable " + std::to_string(mode));
            const auto closeError = retryView.persistenceStatus();
            check(!retryView.requestClose() && !retryView.requestClose()
                      && retryView.closeState() == FreeplayView::CloseState::Blocked
                      && retryView.persistenceStatus() == closeError
                      && retryView.activeNanoseconds() == 2'000'000'000ULL
                      && retryView.historyWriteCount() == 0,
                  "failed or lost receipt blocks repeated Quit and retains the exact original error and time " + std::to_string(mode));
            auto heldCloseFuture = store.snapshot("fault-held-close-" + std::to_string(mode));
            check(storage::ProfileStore::waitForAcknowledgment(heldCloseFuture).data.object().at("authoritative")
                      == beforeRetry.data.object().at("authoritative"),
                  "repeated failed Quit submits no retry or replacement history operation " + std::to_string(mode));
            check(retryView.retryPersistence() && !retryView.retryPersistence()
                      && !retryView.startFreeplay() && !retryView.stopFreeplay(),
                  "explicit retry retains one operation and prevents concurrent transport " + std::to_string(mode));
            for (int attempt = 0; attempt < 4000 && !retryView.persistenceSaved(); ++attempt) {
                retryView.servicePersistence();
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
            auto afterRetryFuture = store.snapshot("fault-after-retry-" + std::to_string(mode));
            const auto afterRetry = storage::ProfileStore::waitForAcknowledgment(afterRetryFuture);
            const auto& beforeRows = beforeRetry.data.object().at("authoritative");
            const auto& afterRows = afterRetry.data.object().at("authoritative");
            const auto originalCount = beforeRows.object().at("identity").array().size();
            check(retryView.persistenceSaved() && retryView.canLeave() && retryView.historyWriteCount() == 1
                      && retryView.activeNanoseconds() == 2'000'000'000ULL
                      && afterRows.object().at("identity").array().size() == originalCount + (mode == 1 ? 1 : 0)
                      && afterRows.object().at("finalized").array().size() == static_cast<std::size_t>(2 + mode)
                      && afterRows.object().at("pending").array().empty()
                      && afterRows.object().at("session").array().empty(),
                  "retry confirms one original without duplicate identity or curriculum credit " + std::to_string(mode));
            check(retryView.requestClose() && retryView.closeState() == FreeplayView::CloseState::Ready
                      && retryView.historyWriteCount() == 1,
                  "explicit original retry restores Quit readiness without another history save " + std::to_string(mode));
            if (mode != 1)
                check(afterRows.object().at("identity") == beforeRows.object().at("identity"),
                      "save retry preserves the exact original owner and context " + std::to_string(mode));
            if (mode == 3)
                check(afterRows.object().at("finalized") == beforeRows.object().at("finalized"),
                      "lost receipt retry preserves the already committed original byte for byte");
            if (mode == 2) {
                const auto& originalPending = beforeRows.object().at("pending").array();
                bool exactSealedOriginal = originalPending.size() == 1;
                if (exactSealedOriginal) {
                    bool matching = false;
                    for (const auto& row : afterRows.object().at("finalized").array())
                        matching = matching || (row.array().at(0) == originalPending.front().array().at(0)
                            && row.array().at(1) == originalPending.front().array().at(2));
                    exactSealedOriginal = matching;
                }
                check(exactSealedOriginal, "failed commit retry finalizes the exact previously sealed owner and payload");
            }
        }

        FreeplayView zeroConfigured;
        zeroConfigured.setClockForTest([] { return std::uint64_t{0}; });
        check(zeroConfigured.configureStore(store, [] { return std::string("2026-09-13T18:08:30Z"); }, "America/New_York")
                  && zeroConfigured.startFreeplay() && zeroConfigured.pauseFreeplay() && zeroConfigured.stopFreeplay(),
              "normal zero-time paused activity explicitly requests its own stopped save");
        for (int attempt = 0; attempt < 4000 && !zeroConfigured.persistenceSaved(); ++attempt) {
            zeroConfigured.servicePersistence();
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        check(zeroConfigured.persistenceSaved() && zeroConfigured.canLeave()
                  && zeroConfigured.activeNanoseconds() == 0 && zeroConfigured.historyWriteCount() == 1
                  && !zeroConfigured.stopFreeplay(),
              "normal Ready path still confirms one truthful zero-time original");

        // Lost allocation receipt and late allocation cancel the unchanged
        // capture before Ready. They cannot bind the already-stopped timer by
        // inspecting a zero-frame canceled capture, so retain debt honestly.
        for (const int mode : {4, 5}) {
            const auto unresolvedDirectory = evidence / ("unresolved-allocation-" + std::to_string(mode));
            std::filesystem::create_directories(unresolvedDirectory);
            std::filesystem::permissions(unresolvedDirectory, std::filesystem::perms::owner_all,
                                         std::filesystem::perm_options::replace);
            storage::StoreOptions unresolvedOptions;
            unresolvedOptions.path = unresolvedDirectory / "profile.sqlite";
            unresolvedOptions.create = true;
            unresolvedOptions.createdUtc = "2026-09-13T18:08:00Z";
            std::atomic<int> allocationFault{mode};
            std::atomic<int> inspections{};
            unresolvedOptions.diagnosticHook = [&](const std::string& phase, const std::string& operation) {
                if (phase == "before_operation" && operation.find(".inspect") != std::string::npos)
                    ++inspections;
                if (operation.find(".allocate") != std::string::npos
                    && phase == (mode == 4 ? "after_commit" : "before_operation")
                    && allocationFault.exchange(0) == mode) {
                    if (mode == 4)
                        throw std::runtime_error("Controlled lost Freeplay allocation receipt");
                    std::this_thread::sleep_for(std::chrono::milliseconds(1100));
                }
            };
            storage::ProfileStore unresolvedStore(unresolvedOptions);
            FreeplayView unresolved;
            unresolved.setSize(920, 680);
            std::uint64_t unresolvedNow{};
            unresolved.setClockForTest([&unresolvedNow] { return unresolvedNow; });
            check(unresolved.configureStore(unresolvedStore, [] { return std::string("2026-09-13T18:08:30Z"); },
                                            "America/New_York") && unresolved.startFreeplay(),
                  "unresolved allocation fixture starts its own activity " + std::to_string(mode));
            unresolvedNow = 2'000'000'000ULL;
            check(unresolved.stopFreeplay(), "unresolved allocation explicitly stops nonzero time " + std::to_string(mode));
            for (int attempt = 0; attempt < 4000 && unresolved.persistencePending(); ++attempt) {
                unresolved.servicePersistence();
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
            const auto* retry = dynamic_cast<const juce::TextButton*>(unresolved.findChildWithID("freeplay-retry-save"));
            check(!unresolved.persistencePending() && !unresolved.persistenceSaved() && !unresolved.canLeave()
                      && allocationFault == 0 && unresolved.activeNanoseconds() == 2'000'000'000ULL
                      && unresolved.timerText() == "00:00:02" && unresolved.historyWriteCount() == 0
                      && retry && retry->isVisible() && !retry->isEnabled()
                      && unresolved.persistenceStatus().find(mode == 4 ? "allocation is unresolved" : "duration is not bound")
                          != std::string::npos,
                  "unknown or canceled allocation retains two seconds and truthful disabled retry " + std::to_string(mode));
            const auto unresolvedCloseError = unresolved.persistenceStatus();
            check(!unresolved.requestClose() && !unresolved.requestClose()
                      && unresolved.closeState() == FreeplayView::CloseState::Blocked
                      && unresolved.persistenceStatus() == unresolvedCloseError
                      && unresolved.activeNanoseconds() == 2'000'000'000ULL,
                  "ambiguous original allocation holds repeated Quit with its exact error and retained time " + std::to_string(mode));
            auto retainedFuture = unresolvedStore.snapshot("unresolved-retained-" + std::to_string(mode));
            const auto retained = storage::ProfileStore::waitForAcknowledgment(retainedFuture);
            const auto& retainedRows = retained.data.object().at("authoritative");
            check(retained.status == storage::Status::Confirmed
                      && retainedRows.object().at("identity").array().size() == 1
                      && retainedRows.object().at("identity").array().front().array().at(0).isString()
                      && !retainedRows.object().at("identity").array().front().array().at(0).string().empty()
                      && retainedRows.object().at("finalized").array().empty()
                      && retainedRows.object().at("pending").array().empty()
                      && retainedRows.object().at("session").array().empty(),
                  "original allocation owner retained without zero-duration finalization or lesson Session " + std::to_string(mode));
            check(!unresolved.retryPersistence() && !unresolved.retryPersistence() && !unresolved.startFreeplay()
                      && !unresolved.stopFreeplay() && !unresolved.pauseFreeplay()
                      && !unresolved.requestBack() && !unresolved.requestProgress()
                      && !unresolved.requestRhythmTools() && !unresolved.requestAudioSettings()
                      && !unresolved.configureStore(unresolvedStore, [] { return std::string("2026-09-13T18:08:30Z"); },
                                                    "America/New_York"),
                  "unsupported allocation recovery refuses inspection replacement and navigation " + std::to_string(mode));
            unresolved.servicePersistence();
            auto unchangedFuture = unresolvedStore.snapshot("unresolved-unchanged-" + std::to_string(mode));
            const auto unchanged = storage::ProfileStore::waitForAcknowledgment(unchangedFuture);
            check(unchanged.status == storage::Status::Confirmed
                      && unchanged.data.object().at("authoritative") == retainedRows
                      && inspections == 0 && unresolved.activeNanoseconds() == 2'000'000'000ULL
                      && unresolved.historyWriteCount() == 0 && !unresolved.persistenceSaved(),
                  "refused recovery preserves exact owner and original rows without inspection or fake success " + std::to_string(mode));
        }

        std::ofstream summary(evidence / "summary.json");
        summary << "{\"checks\":" << count << ",\"status\":\"PASS\"}\n";
        std::cout << "PASS " << count << " Freeplay checks\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL after " << count << ": " << error.what() << '\n';
        return 1;
    }
}
