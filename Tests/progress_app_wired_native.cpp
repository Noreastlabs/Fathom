// One running Home/Progress path. Only the device-open leaf is software backed.
#define main retained_shared_audio_campaign_main
#include "shared_audio_settings_tests.cpp"
#undef main

#include <fstream>

int main(int argc, char** argv) {
 int checks = 0;
 try {
  if (argc != 4 || std::string(argv[1]) != "--app-wired-progress")
   throw std::runtime_error("Usage: fathom_progress_app_native --app-wired-progress <absolute bundle> <new absolute output>");
  const std::filesystem::path bundle = argv[2], root = argv[3];
  if (!bundle.is_absolute() || !root.is_absolute() || !std::filesystem::is_directory(bundle) || std::filesystem::exists(root))
   throw std::runtime_error("Absolute retained bundle and absent absolute output directory required");
  std::filesystem::create_directory(root);
  std::filesystem::permissions(root, std::filesystem::perms::owner_all);
  std::ofstream checkFile(root / "checks.tsv"), keyFile(root / "keys.tsv");
  auto ck = [&](bool okay, const std::string& label) {
   ++checks; checkFile << label << '\t' << (okay ? "PASS" : "FAIL") << '\n'; checkFile.flush();
   if (!okay) throw std::runtime_error(label);
  };
  [NSApplication sharedApplication];
  [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
  juce::ScopedJuceInitialiser_GUI gui;
  Harness h(root, "app-wired");
  h.home->addToDesktop(juce::ComponentPeer::windowHasTitleBar);
  h.home->setVisible(true);
  ck(A::lessons(*h.home).load(bundle), "retained representative bundle loads in Home");
  ck(h.home->page() == H::Page::Home && h.finals() == 0 && nativeOpens == 0,
     "attached Home starts with no finalized activity or native output");
  auto* peer = h.home->getPeer();
  NSView* native = peer ? (__bridge NSView*) peer->getNativeHandle() : nil;
  ck(native && native.window, "Home has a native window");
  [NSApp activateIgnoringOtherApps:YES];
  [native.window makeKeyAndOrderFront:nil];
  const auto activeDeadline = capture_fixture::now() + 2000;
  while ((! [NSApp isActive] || !native.window.isKeyWindow) && capture_fixture::now() < activeDeadline) pump();
  ck([NSApp isActive] && native.window.isKeyWindow, "application is active with a key Home window");
  keyFile << "control\tkey_code\tapp_active\tkey_window\tbutton_focused\tresult\n";
  const auto tapSpace = [&](juce::Button& control, const char* label) {
   control.grabKeyboardFocus();
   const auto focusDeadline = capture_fixture::now() + 2000;
   while (!control.hasKeyboardFocus(false) && capture_fixture::now() < focusDeadline) pump();
   ck(control.hasKeyboardFocus(false), std::string(label) + " owns JUCE keyboard focus");
   for (bool down : {true, false}) {
    auto* event = [NSEvent keyEventWithType:down ? NSEventTypeKeyDown : NSEventTypeKeyUp
       location:NSZeroPoint modifierFlags:0 timestamp:NSProcessInfo.processInfo.systemUptime
       windowNumber:native.window.windowNumber context:nil characters:@" " charactersIgnoringModifiers:@" "
       isARepeat:NO keyCode:49];
    [NSApp sendEvent:event];
   }
   keyFile << label << "\t49\t" << [NSApp isActive] << '\t' << native.window.isKeyWindow
           << '\t' << control.hasKeyboardFocus(false) << "\tconstructed AppKit down/up\n";
  };
  tapSpace(button(*h.home, "Progress"), "Home Progress");
  h.wait([&] { return h.home->page() == H::Page::Progress; }, "Home Progress keyboard route");
  auto& progress = A::progress(*h.home);
  h.wait([&] { return !progress.busy(); }, "empty Progress read");
  ck(progress.isShowing() && progress.presentation().text.find("No finalized practice activity in this snapshot.") != std::string::npos,
     "foreground Home keyboard action opens truthful attached empty Progress");
  ck(progress.statusText().find("does not award curriculum credit") != std::string::npos &&
     progress.presentation().text.find("Start with Learn") != std::string::npos,
     "empty Progress shows read-only no-credit boundary and next action");
  ck(h.finals() == 0 && nativeOpens == 0 && !h.practice().captureSession()->startTaken(),
     "empty Progress creates no Attempt or native output");
  h.image("empty-progress");
  tapSpace(button(progress, "Back"), "Progress Back");
  h.wait([&] { return h.home->page() == H::Page::Home; }, "empty Progress Back keyboard route");
  ck(h.finals() == 0, "foreground Back returns Home without activity");

  click(*h.home, "Learn");
  auto& learn = A::lessons(*h.home);
  ck(h.home->page() == H::Page::Learn && learn.selectLesson("fg:item:000002") &&
     learn.selectVariant("fg:variant:000006"), "Learn selects retained admitted L3 case");
  const auto admission = learn.catalog()->admit("fg:item:000002", "fg:variant:000006");
  ck(admission && admission->practiceAllowed() &&
     admission->model()->source().sourceRefs == std::vector<std::string>{"L3-TXT5-21", "L3-TXT28-46"},
     "exact L3 admission and source refs are retained");
  click(learn, "Practice selected case");
  h.wait([&] { return h.home->page() == H::Page::Practice; }, "L3 Practice entry");
  ck(h.practice().lessonAdmission() &&
     storage::canonical(h.practice().lessonAdmission()->identity()) == storage::canonical(admission->identity()) &&
     h.practice().captureSessionId() == h.sessionId,
     "actual Practice retains exact L3 admission and original Session");
  click(h.practice(), "Audio settings");
  h.wait([&] { return h.home->page() == H::Page::Audio; }, "shared Audio settings");
  auto& audio = A::settings(*h.home);
  click(audio, "Connect audio"); h.tick(); click(audio, "Enable audio"); h.blocks(1);
  h.wait([&] { return h.home->audioSettings().snapshot().state == output::State::Ready; }, "software audio ready");
  click(audio, "Back to Practice");
  h.wait([&] { return h.home->page() == H::Page::Practice; }, "Practice return");
  click(h.practice(), "Start selected case");
  h.wait([&] { return h.practice().captureSession()->startTaken(); }, "explicit Practice Start");
  h.blocks(1);
  ck(h.finals() == 0, "explicit Start has no finalized Attempt yet");
  click(h.practice(), "Stop & review result");
  h.wait([&] { return h.practice().captureSession()->phase() == capture::SessionPhase::Review; }, "Practice Review");
  click(h.practice(), "Save result");
  h.wait([&] { return h.practice().captureSession()->phase() == capture::SessionPhase::Saved; }, "Practice Save");
  h.blocks(2);
  h.wait([&] { return h.practice().audioCanRelease(); }, "software audio cleanup");
  const auto saved = capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  const auto savedAuthority = storage::canonical(*saved.data.find("authoritative"));
  const auto original = progression::adaptSnapshot(saved).originalHistory;
  const auto attempt = std::find_if(original.begin(), original.end(), [](const auto& row) {
   return row.object().at("kind").string() == "Attempt";
  });
  ck(h.finals() == 1 && attempt != original.end() && h.practice().captureSessionId() == h.sessionId,
     "one valid L3 Attempt was finalized with original Practice Session unchanged");
  const auto envelope = storage::validateEnvelope(attempt->object().at("bytes").string());
  ck(envelope.value.object().at("context").object().at("item_id").string() == "fg:item:000002" &&
     envelope.value.object().at("context").object().at("variant_id").string() == "fg:variant:000006",
     "saved original has exact item and variant provenance");
  click(h.practice(), "Open Progress");
  h.wait([&] { return h.home->page() == H::Page::Progress && !progress.busy(); }, "saved Progress route");
  const auto body = progress.presentation().text;
  ck(progress.isShowing() && body.find("Finalized local activity records in this snapshot: 1") != std::string::npos &&
     body.find("Attempts: 1") != std::string::npos,
     "saved Progress shows one Attempt in read-only history");
  ck(body.find("fg:item:000002 / fg:variant:000006") != std::string::npos &&
     body.find("Source: L3-TXT5-21 L3-TXT28-46") != std::string::npos &&
     body.find("Content version: representative-controls.1") != std::string::npos &&
     body.find("Content revision: 2") != std::string::npos &&
     body.find("Original: " + envelope.owner) != std::string::npos,
     "saved Progress visibly preserves exact source and original Attempt owner");
  ck(body.find("Source-task completion credited: no") != std::string::npos &&
     progress.statusText().find("does not award curriculum credit") != std::string::npos,
     "saved Progress avoids invented completion and curriculum credit");
  h.image("saved-progress");
  const auto progressReads = [&] {
   std::ifstream hooks(h.dir / "hooks.tsv");
   std::string line;
   int count = 0;
   while (std::getline(hooks, line))
    if (line.rfind("before_operation\tprogress-view/", 0) == 0) ++count;
   return count;
  };
  const auto beforeRefresh = progressReads();
  tapSpace(button(progress, "Refresh"), "Progress Refresh");
  h.wait([&] { return progressReads() == beforeRefresh + 1 && !progress.busy(); }, "foreground Progress Refresh");
  ck(progressReads() == beforeRefresh + 1 && progress.presentation().text == body && h.finals() == 1,
     "foreground keyboard Refresh executes one Store read, keeping exact saved view and one Attempt");
  click(progress, "Show saved details");
  h.tick();
  auto* editor = dynamic_cast<juce::TextEditor*>(progress.findChildWithID("progress-body"));
  ck(editor && editor->getText().toStdString() == progress.presentation().details && h.finals() == 1,
     "real Details button exposes retained read-only projection");
  click(progress, "Hide saved details");
  h.tick();
  ck(editor->getText().toStdString() == body, "Hide details restores saved Progress body");
  const auto after = capture_fixture::confirmed(h.store->snapshot(storage::newUuid()));
  ck(storage::canonical(*after.data.find("authoritative")) == savedAuthority &&
     after.data.find("authoritative")->find("finalized")->array().size() == 1 && nativeOpens == 0,
     "Progress reads, keyboard and details leave authoritative Store and native output unchanged");
  click(progress, "Back");
  h.wait([&] { return h.home->page() == H::Page::Home; }, "saved Progress Back to Home");
  ck(h.finals() == 1 && h.home->audioSettings().snapshot().state == output::State::Closed,
     "saved Progress Back retains one Attempt and closed output");
  ck(h.home->requestClose(), "Home closes cleanly after saved Progress");
  checkFile.flush(); keyFile.flush();
  ck(checkFile.good() && keyFile.good(), "Progress evidence flushed");
  std::ofstream(root / "summary.json") << "{\"status\":\"PASS\",\"checks\":" << checks
     << ",\"savedAttempts\":1,\"softwareDevice\":true,\"constructedForegroundKeys\":true,"
     << "\"physicalUserKeys\":\"NOT RUN\",\"humanAssistiveReview\":\"NOT RUN\","
     << "\"nativeOpens\":" << nativeOpens << "}\n";
  std::cout << "PASS " << checks << " app-wired Progress checks; physical keys and human review NOT RUN\n";
  return 0;
 } catch (const std::exception& error) {
  std::cerr << "FAIL after " << checks << " checks: " << error.what() << '\n'; return 1;
 }
}
