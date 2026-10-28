// Fresh app-wired compact Focus route. The output-device leaf is software backed.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main

#include <algorithm>
#include <fstream>
#include <vector>

int main(int argc, char** argv) {
 int checks = 0;
 try {
  if (argc != 4 || std::string(argv[1]) != "--compact-app-focus")
   throw std::runtime_error("Usage: fathom_focus_compact_app_native --compact-app-focus <absolute bundle> <new absolute output>");
  const std::filesystem::path bundle = argv[2], root = argv[3];
  if (!bundle.is_absolute() || !root.is_absolute() || !std::filesystem::is_directory(bundle) || std::filesystem::exists(root))
   throw std::runtime_error("Absolute retained bundle and absent absolute output required");
  std::filesystem::create_directory(root);
  std::filesystem::permissions(root, std::filesystem::perms::owner_all);
  std::ofstream checkFile(root / "checks.tsv"), keyFile(root / "keys.tsv"), geometry(root / "geometry.tsv");
  auto ck = [&](bool okay, const std::string& name) {
   ++checks; checkFile << name << '\t' << (okay ? "PASS" : "FAIL") << '\n'; checkFile.flush();
   if (!okay) throw std::runtime_error(name);
  };
  [NSApplication sharedApplication];
  [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
  juce::ScopedJuceInitialiser_GUI gui;
  Harness h(root, "app-wired");
  h.home->setSize(640, 680);
  h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);
  h.home->setVisible(true);
  ck(A::lessons(*h.home).load(bundle), "retained representative bundle loads in actual Home");
  click(*h.home, "Learn");
  auto& learn = A::lessons(*h.home);
  ck(h.home->page() == H::Page::Learn && learn.selectLesson("fg:item:000002") &&
     learn.selectVariant("fg:variant:000006"), "compact Home opens Learn and selects admitted L3");
  const auto admission = learn.catalog()->admit("fg:item:000002", "fg:variant:000006");
  ck(admission && admission->practiceAllowed() &&
     admission->model()->source().sourceRefs == std::vector<std::string>{"L3-TXT5-21", "L3-TXT28-46"},
     "admitted L3 keeps exact authored refs");
  const auto before = capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  const auto beforeAuthority = storage::canonical(*before.data.find("authoritative"));
  click(learn, "Practice selected case");
  h.wait([&] { return h.home->page() == H::Page::Practice; }, "compact Learn to Practice");
  auto& practice = h.practice();
  ck(practice.lessonAdmission() &&
     storage::canonical(practice.lessonAdmission()->identity()) == storage::canonical(admission->identity()) &&
     practice.captureSessionId() == h.sessionId && practice.tabVisible(),
     "Practice retains exact L3 admission, original Session and authored TAB");
  NSView* native = practice.getPeer() ? (__bridge NSView*) practice.getPeer()->getNativeHandle() : nil;
  ck(native && native.window && practice.isShowing(), "compact Practice has a visible native window");
  [NSApp activateIgnoringOtherApps:YES];
  [native.window makeKeyAndOrderFront:nil];
  practice.grabKeyboardFocus();
  const auto focusDeadline = capture_fixture::now() + 2000;
  while ((! [NSApp isActive] || !native.window.isKeyWindow || !practice.hasKeyboardFocus(false)) &&
         capture_fixture::now() < focusDeadline) pump();
  ck([NSApp isActive] && native.window.isKeyWindow && practice.hasKeyboardFocus(false),
     "foreground app, key window and Practice focus are active");
  keyFile << "key\thardware\tdown\tmatched\tvisible\tinvoked\n";
  std::vector<desktop::PracticeKeyObservation> observed;
  int invocations = 0;
  practice.onKeyObservation = [&](const desktop::PracticeKeyObservation& event) {
   observed.push_back(event); invocations += event.invoked;
   keyFile << event.key << '\t' << event.hardwareKey << '\t' << event.down << '\t'
           << event.matchedWindow << '\t' << event.visible << '\t' << event.invoked << '\n';
  };
  const auto tap = [&](NSString* value, unsigned short code) {
   for (bool down : {true, false}) {
    auto* event = [NSEvent keyEventWithType:down ? NSEventTypeKeyDown : NSEventTypeKeyUp
       location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime
       windowNumber:native.window.windowNumber context:nil characters:value charactersIgnoringModifiers:value
       isARepeat:NO keyCode:code];
    [NSApp sendEvent:event];
   }
  };
  const auto picture = [&](int width, int height, const std::string& label) {
   h.home->setSize(width, height);
   h.tick();
   auto shot = h.home->createComponentSnapshot(h.home->getLocalBounds());
   juce::FileOutputStream out(juce::File((root / (label + "-" + std::to_string(width) + ".png")).string()));
   juce::PNGImageFormat png;
   ck(out.openedOk() && png.writeImageToStream(shot, out), label + " screenshot written at " + std::to_string(width));
   out.flush();
  };
  tap(@"f", 3);
  ck(practice.focusMode() && invocations == 1 && observed.size() == 2 && practice.tabView().isVisible(),
     "foreground F enters app-wired compact Focus once with TAB visible");
  const auto focusFacts = practice.focusFacts();
  ck(focusFacts.find("Selected: 60 BPM") != std::string::npos &&
     focusFacts.find("Current: 60 BPM") != std::string::npos &&
     focusFacts.find("Target:") != std::string::npos && focusFacts.find("Scheduled:") != std::string::npos &&
     focusFacts.find("Practice owner Session: " + h.sessionId) != std::string::npos,
     "compact Focus visibly retains selected/current BPM, loop and exact Session");
  juce::Viewport* viewport = nullptr;
  juce::TextButton* larger = nullptr;
  for (auto* child : practice.tabView().getChildren()) {
   if (auto* candidate = dynamic_cast<juce::Viewport*>(child)) viewport = candidate;
   if (auto* candidate = dynamic_cast<juce::TextButton*>(child);
       candidate && candidate->getButtonText() == "A+") larger = candidate;
  }
  ck(viewport && larger && viewport->isVisible() && viewport->getHeight() >= 70 &&
     viewport->getViewedComponent() && viewport->getViewedComponent()->getHeight() > viewport->getHeight() &&
     viewport->getY() >= larger->getBottom(),
     "640px app-wired Focus exposes at least 70px scrollable authored TAB canvas below A controls");
  auto* start = practice.findChildWithID("practice-start");
  auto* clean = practice.findChildWithID("practice-clean");
  auto* save = practice.findChildWithID("practice-save");
  auto* again = practice.findChildWithID("practice-again");
  auto* status = dynamic_cast<juce::Label*>(practice.findChildWithID("practice-status"));
  ck(start && clean && save && again && status && start->isVisible() && clean->isVisible() &&
     save->isVisible() && again->isVisible() &&
     practice.getLocalBounds().contains(practice.tabView().getBounds()) &&
     practice.tabView().getBottom() <= start->getY() &&
     status->getText().contains("Source refs: L3-TXT5-21, L3-TXT28-46"),
     "640px TAB, transport, Clean/Save/Again and source status remain visible and contained");
  geometry << "width\theight\ttab_height\tcanvas_height\tcanvas_content_height\tstart_y\n";
  geometry << 640 << '\t' << 680 << '\t' << practice.tabView().getHeight() << '\t'
           << viewport->getHeight() << '\t' << viewport->getViewedComponent()->getHeight() << '\t'
           << start->getY() << '\n';
  picture(640, 680, "focus");
  tap(@" ", 49);
  ck(invocations == 2 && practice.outputStatus().lifecycle.state == output::State::Closed &&
     !practice.captureSession()->startTaken() && !practice.commandFeedback().empty(),
     "compact foreground Space visibly refuses Start with output Closed");
  tap(@"c", 8);
  ck(invocations == 3 && practice.commandFeedback().find("Clean requires an ended result") != std::string::npos,
     "compact Clean refusal remains visible before Review");
  tap(@"a", 0);
  ck(invocations == 4 && practice.commandFeedback().find("Again requires confirmed persistence") != std::string::npos,
     "compact Again refusal remains visible before Save");
  picture(640, 680, "refused-focus");
  for (const auto& [width, height] : {std::pair{920, 680}, std::pair{1280, 800}}) {
   h.home->setSize(width, height); h.tick();
   ck(practice.focusMode() && practice.tabView().isVisible() &&
      practice.getLocalBounds().contains(practice.tabView().getBounds()) &&
      viewport->isVisible() && viewport->getHeight() > 70 &&
      start->isVisible() && clean->isVisible() && save->isVisible() && again->isVisible(),
      "normal-width Focus keeps authored TAB and essential commands contained at " + std::to_string(width));
   geometry << width << '\t' << height << '\t' << practice.tabView().getHeight() << '\t'
            << viewport->getHeight() << '\t' << viewport->getViewedComponent()->getHeight() << '\t'
            << start->getY() << '\n';
   picture(width, height, "focus");
  }
  h.home->setSize(640, 680); h.tick();
  tap(@"f", 3);
  ck(!practice.focusMode() && invocations == 5 && observed.size() == 10,
     "second foreground F exits Focus once without changing the result");
  for (const auto& event : observed)
   ck(event.matchedWindow && event.visible && event.invoked == event.down,
      "constructed foreground key invokes only on key down in matching visible window");
  click(practice, "Back");
  h.wait([&] { return h.home->page() == H::Page::Learn; }, "Focus Back to Learn");
  ck(learn.selectedLesson() == "fg:item:000002" && learn.selectedVariant() == "fg:variant:000006" &&
     practice.captureSessionId() == h.sessionId,
     "Back preserves the admitted Learn source and original Session");
  const auto after = capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  ck(storage::canonical(*after.data.find("authoritative")) == beforeAuthority &&
     after.data.find("authoritative")->find("finalized")->array().empty() &&
     h.finals() == 0 && nativeOpens == 0 && practice.coordinator().completedCycles() == 0,
     "compact and normal Focus leave authoritative Store, Attempt and native output unchanged");
  ck(h.home->requestClose(), "app-wired compact Focus closes cleanly");
  checkFile.flush(); keyFile.flush(); geometry.flush();
  ck(checkFile.good() && keyFile.good() && geometry.good(), "compact Focus evidence flushed");
  std::ofstream(root / "summary.json") << "{\"status\":\"PASS\",\"checks\":" << checks
   << ",\"source\":\"fg:item:000002/fg:variant:000006\",\"appWired\":true,"
   << "\"constructedForegroundKeys\":true,\"physicalGuitarHeldKeys\":\"NOT RUN\","
   << "\"humanDistanceReview\":\"NOT RUN\",\"attemptCreated\":false,\"nativeOpens\":0}\n";
  std::cout << "PASS " << checks << " compact app-wired Focus checks; physical/human input NOT RUN\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1;
 }
}
