#include "desktop/Appearance.hpp"
#include "desktop/GuidedSessionView.hpp"
#include "content/Canonical.hpp"
#include "platform/ProfileAccessMac.hpp"

#include <algorithm>
#include <array>
#include <charconv>
#include <ctime>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <vector>

namespace fathom::desktop {
namespace {
using V = json::Value;
const std::array<int, 5> presets{10, 20, 30, 45, 60};
constexpr const char* fullGuidedExplanation =
    "Build a short offline practice plan from the retained Development Preview.\n\n"
    "Choose 10, 20, 30, 45 or 60 minutes, or enter a custom whole-minute duration from 1 to 240.\n\n"
    "Starting a plan creates one local Session; it does not create an exercise attempt, mastery or curriculum progress.\n\n"
    "After Start: choose Prepare selected case in Practice. It opens stopped. Choose explicit Practice Start and Save, then Guided summary returns here with the saved linkage. The active Guided Session owns that Attempt; it remains separate from curriculum credit.\n\n"
    "Refused cases remain out of Practice; an unresolved close stays retryable.\n\n"
    "Local Guided activity requires an explicit profile; for a disposable Development Preview, launch with --capture-preview <new private directory> <IANA timezone>.";
constexpr const char* linkedGuidedExplanation =
    "Saved Practice Attempt belongs to this Guided Session; no curriculum credit.\n"
    "Stop & save summary closes its local Session.";
constexpr const char* compactGuidedExplanation =
    "Build a source-backed Guided plan. Choose a duration before Start.\n"
    "Start creates a local Session; Practice grants no curriculum credit.";
std::string utf8(const juce::String& value) { return value.toStdString(); }
std::string plannedDurationText(const std::int64_t seconds) {
    if (seconds > 0 && seconds % 60 == 0)
        return "Duration: " + std::to_string(seconds / 60) + " minutes (" + std::to_string(seconds) + " seconds)";
    return "Planned duration: " + std::to_string(seconds) + " seconds";
}
std::string outcomeDisplayText(const std::string& outcome) {
    if (outcome == "complete") return "complete (planned duration reached)";
    if (outcome == "partial") return "partial (stopped before planned duration)";
    return outcome;
}
V planItem(const lesson::Lesson& lesson) {
    return V::Object{{"item_id", lesson.id}, {"title", lesson.title}, {"level", V::fromInteger(lesson.level)}};
}
std::string admissionDisclosure(const lesson::Catalog& catalog, const lesson::Lesson& lesson) {
    std::vector<std::string> admitted;
    for (const auto& variant : lesson.variants) {
        try {
            const auto admission = catalog.admit(lesson.id, variant.id);
            if (admission && admission->practiceAllowed()) admitted.push_back(variant.id);
        } catch (const std::exception&) {
            // The existing admission contract refuses unsupported variants. The
            // plan exposes that refusal without inventing a fallback case.
        }
    }
    if (admitted.empty()) return " | Practice admission: refused by the existing runtime gate.";
    std::string text = " | Practice-ready variants: ";
    for (std::size_t index = 0; index < admitted.size(); ++index) {
        if (index != 0) text += ", ";
        text += admitted[index];
    }
    return text;
}
struct AttemptIdentity {
    std::string itemId, variantId;
    std::string contentVersion;
    std::string contentRevision;
    std::vector<std::string> sourceRefs;
};
struct RestoredSummary {
    std::string sessionId, outcome;
    std::int64_t plannedSeconds{}, elapsedSeconds{};
    bool savedAttemptLinked{};
    std::optional<AttemptIdentity> savedAttemptIdentity;
};
struct UnresolvedSummary {
    std::string sessionId;
    std::int64_t plannedSeconds{};
    bool savedAttemptLinked{};
    std::optional<AttemptIdentity> savedAttemptIdentity;
    bool validatedOriginal{};
};
struct SnapshotSummary {
    std::optional<RestoredSummary> saved;
    std::optional<UnresolvedSummary> unresolved;
};
std::optional<AttemptIdentity> readAttemptIdentity(const V& row) {
    try {
        if (!row.isArray() || row.array().size() != 5 || !row.array()[4].isObject()) return std::nullopt;
        const auto* encoded = row.array()[4].find("blob_hex");
        if (!encoded || !encoded->isString()) return std::nullopt;
        const auto& hex = encoded->string();
        if (hex.size() % 2 != 0 || hex.find_first_not_of("0123456789abcdef") != std::string::npos) return std::nullopt;
        std::string bytes;
        bytes.reserve(hex.size() / 2);
        const auto nibble = [](const char c) -> unsigned {
            return c <= '9' ? static_cast<unsigned>(c - '0') : static_cast<unsigned>(c - 'a' + 10);
        };
        for (std::size_t i = 0; i < hex.size(); i += 2)
            bytes.push_back(static_cast<char>((nibble(hex[i]) << 4) | nibble(hex[i + 1])));
        const auto context = storage::parseCanonical(bytes);
        const auto* item = context.find("item_id");
        const auto* variant = context.find("variant_id");
        if (!item || !item->isString() || item->string().empty() || !variant || !variant->isString() || variant->string().empty())
            return std::nullopt;
        AttemptIdentity identity{item->string(), variant->string(), {}, {}, {}};
        if (const auto* contentVersion = context.find("content_version"); contentVersion && contentVersion->isString())
            identity.contentVersion = contentVersion->string();
        if (const auto* contentRevision = context.find("content_revision"))
            identity.contentRevision = storage::canonical(*contentRevision);
        if (const auto* refs = context.find("source_refs"); refs && refs->isArray()) {
            for (const auto& ref : refs->array()) {
                if (!ref.isString()) { identity.sourceRefs.clear(); break; }
                identity.sourceRefs.push_back(ref.string());
            }
        }
        return identity;
    } catch (const std::exception&) {
        return std::nullopt;
    }
}
std::string attemptDetailsText(const std::optional<AttemptIdentity>& identity, const lesson::Catalog* catalog = nullptr) {
    if (!identity) return {};
    std::string text = "\nSource case: " + identity->itemId + " / " + identity->variantId;
    if (catalog) {
        try {
            const auto& record = catalog->lesson(identity->itemId).record.object();
            text += "\nWorkbook identity: " + record.at("workbook_id").string() + " | Level: " + storage::canonical(record.at("legacy_level"));
            text += "\nLesson title: " + record.at("title").string();
            text += "\nVariant label: " + catalog->variant(identity->itemId, identity->variantId).label;
        } catch (const std::exception&) {
            // Preserve the existing source details when the loaded catalog cannot resolve this identity.
        }
    }
    if (!identity->sourceRefs.empty()) {
        text += "\nSource refs: ";
        for (std::size_t i = 0; i < identity->sourceRefs.size(); ++i) {
            if (i != 0) text += ", ";
            text += identity->sourceRefs[i];
        }
    }
    if (!identity->contentVersion.empty()) text += "\nContent version: " + identity->contentVersion;
    if (!identity->contentRevision.empty()) text += "\nContent revision: " + identity->contentRevision;
    return text;
}
std::string savedAttemptText(const std::optional<AttemptIdentity>& identity, const lesson::Catalog* catalog = nullptr) {
    return "\nSAVED ATTEMPT\nSaved Practice Attempt: linked to this Guided Session." + attemptDetailsText(identity, catalog);
}
std::string savedAttemptText(const bool linked, const std::string& details) {
    return linked ? "\nSAVED ATTEMPT\nSaved Practice Attempt: linked to this Guided Session." + details : std::string{};
}
std::int64_t utcMicros(const std::string& value) {
    storage::validateUtc(value);
    if (value.size() < 20 || value[19] != 'Z') throw std::invalid_argument("Invalid UTC timestamp");
    std::tm tm{};
    tm.tm_year = std::stoi(value.substr(0, 4)) - 1900; tm.tm_mon = std::stoi(value.substr(5, 2)) - 1;
    tm.tm_mday = std::stoi(value.substr(8, 2)); tm.tm_hour = std::stoi(value.substr(11, 2));
    tm.tm_min = std::stoi(value.substr(14, 2)); tm.tm_sec = std::stoi(value.substr(17, 2));
    const auto seconds = timegm(&tm);
    if (seconds < std::numeric_limits<std::int64_t>::min() / 1000000
        || seconds > std::numeric_limits<std::int64_t>::max() / 1000000) throw std::invalid_argument("UTC overflow");
    std::int64_t micros = seconds * 1000000;
    if (value.size() > 20) {
        if (value[19] != '.') throw std::invalid_argument("Invalid UTC precision");
        auto digits = value.substr(20, value.size() - 21);
        if (digits.empty() || digits.size() > 6 || digits.find_first_not_of("0123456789") != std::string::npos)
            throw std::invalid_argument("Invalid UTC precision");
        digits.append(6 - digits.size(), '0');
        micros += std::stoll(digits);
    }
    return micros;
}
bool validatedOriginalGuidedPlan(const V& blob,std::int64_t planned,const std::string& authoritativeOwner){
 try{
  const auto* encoded=blob.find("blob_hex");if(!encoded||!encoded->isString())return false;const auto& hex=encoded->string();
  if(hex.size()%2||hex.size()>2*1024*1024||hex.find_first_not_of("0123456789abcdef")!=std::string::npos)return false;
  const auto nibble=[](char c){return c<='9'?c-'0':c-'a'+10;};std::string bytes;bytes.reserve(hex.size()/2);
  for(std::size_t j=0;j<hex.size();j+=2)bytes.push_back(static_cast<char>((nibble(hex[j])<<4)|nibble(hex[j+1])));
  const auto plan=storage::parseCanonical(bytes);const auto* version=plan.find("version");const auto* seconds=plan.find("planned_seconds");const auto* items=plan.find("items");std::int64_t declared{};
  const auto* boundOwner=plan.find("original_session_id");const auto* boundOperation=plan.find("original_start_operation");
  // Legacy version1 plans have neither bound field. They remain closable by
  // their validated authoritative row; partial or contradictory bindings fail closed.
  if(boundOwner||boundOperation){
   if(!boundOwner||!boundOperation||!boundOwner->isString()||boundOwner->string()!=authoritativeOwner||!boundOperation->isString())return false;
   constexpr const char* prefix="guided-session/create/";const auto& operation=boundOperation->string();
   if(operation.rfind(prefix,0)!=0)return false;storage::validateUuid(operation.substr(std::char_traits<char>::length(prefix)));
  }
  const auto* minutes=plan.find("duration_minutes");const auto* content=plan.find("content_version");std::int64_t duration{};
  if(!version||*version!=V("guided-session-plan.1")||!seconds||!seconds->integer(declared)||declared!=planned
     ||!minutes||!minutes->integer(duration)||duration<1||duration>240||duration*60!=planned
     ||!content||!content->isString()||content->string().empty()||content->string().size()>4096
     ||!items||!items->isArray()||items->array().empty()||items->array().size()>10000)return false;
  for(const auto& item:items->array()){
   const auto* id=item.find("item_id");const auto* title=item.find("title");const auto* level=item.find("level");std::int64_t n{};
   if(!id||!id->isString()||id->string().size()!=14||id->string().rfind("fg:item:",0)!=0||id->string().substr(8)=="000000"
      ||!std::all_of(id->string().begin()+8,id->string().end(),[](char c){return c>='0'&&c<='9';})
      ||!title||!title->isString()||title->string().empty()||title->string().size()>4096||!level||!level->integer(n)||n<1||n>105)return false;
  }
  return true;
 }catch(const std::exception&){return false;}
}
SnapshotSummary readSnapshotSummary(const V& snapshot) {
    const auto* authority = snapshot.find("authoritative");
    if (!authority || !authority->isObject()) throw std::invalid_argument("Snapshot has no authoritative object");
    const auto* sessions = authority->find("session");
    const auto* closes = authority->find("session_close");
    if (!sessions || !sessions->isArray() || !closes || !closes->isArray())
        throw std::invalid_argument("Snapshot has no authoritative Guided Session tables");
    std::set<std::string> finalizedOwners;
    if (const auto* finalized = authority->find("finalized"); finalized && finalized->isArray()) {
        for (const auto& row : finalized->array()) {
            if (row.isArray() && !row.array().empty() && row.array()[0].isString())
                finalizedOwners.insert(row.array()[0].string());
        }
    }
    std::set<std::string> savedAttemptSessions;
    std::map<std::string, AttemptIdentity> savedAttemptIdentities;
    if (const auto* identities = authority->find("identity"); identities && identities->isArray()) {
        for (const auto& row : identities->array()) {
            if (!row.isArray() || row.array().size() != 5 || !row.array()[0].isString()
                || !row.array()[1].isString() || !row.array()[2].isString()) continue;
            if (row.array()[1].string() == "Attempt" && finalizedOwners.count(row.array()[0].string()) != 0) {
                savedAttemptSessions.insert(row.array()[2].string());
                if (const auto identity = readAttemptIdentity(row))
                    savedAttemptIdentities.emplace(row.array()[2].string(), *identity);
            }
        }
    }
    const auto attemptIdentityFor = [&](const std::string& sessionId) -> std::optional<AttemptIdentity> {
        const auto found = savedAttemptIdentities.find(sessionId);
        return found == savedAttemptIdentities.end() ? std::nullopt : std::optional<AttemptIdentity>(found->second);
    };
    struct Close { std::string ended, outcome; };
    std::map<std::string, Close> closed;
    const std::set<std::string> outcomes{"complete", "partial", "interrupted", "cancelled"};
    for (const auto& row : closes->array()) {
        if (!row.isArray() || row.array().size() != 3 || !row.array()[0].isString()
            || !row.array()[1].isString() || !row.array()[2].isString()) continue;
        if (outcomes.count(row.array()[2].string()) == 0) continue;
        try { utcMicros(row.array()[1].string()); } catch (const std::exception&) { continue; }
        closed[row.array()[0].string()] = Close{row.array()[1].string(), row.array()[2].string()};
    }
    std::optional<RestoredSummary> latest;
    std::optional<UnresolvedSummary> unresolved;
    std::int64_t latestStarted = std::numeric_limits<std::int64_t>::min();
    std::int64_t latestUnresolvedStarted = std::numeric_limits<std::int64_t>::min();
    for (const auto& row : sessions->array()) {
        if (!row.isArray() || row.array().size() != 5 || !row.array()[0].isString() || !row.array()[1].isString()) continue;
        std::int64_t planned{};
        if (!row.array()[3].integer(planned) || planned <= 0) continue;
        const auto close = closed.find(row.array()[0].string());
        try {
            const auto started = utcMicros(row.array()[1].string());
            if (close == closed.end()) {
                if (started > latestUnresolvedStarted) {
                    latestUnresolvedStarted = started;
                    unresolved = UnresolvedSummary{row.array()[0].string(), planned,
                                                   savedAttemptSessions.count(row.array()[0].string()) != 0,
                                                   attemptIdentityFor(row.array()[0].string()),validatedOriginalGuidedPlan(row.array()[4],planned,row.array()[0].string())};
                }
                continue;
            }
            const auto ended = utcMicros(close->second.ended);
            if (ended < started || started <= latestStarted) continue;
            latestStarted = started;
            latest = RestoredSummary{row.array()[0].string(), close->second.outcome, planned,
                                     (ended - started) / 1000000,
                                     savedAttemptSessions.count(row.array()[0].string()) != 0,
                                     attemptIdentityFor(row.array()[0].string())};
        } catch (const std::exception&) { continue; }
    }
    return SnapshotSummary{latest, unresolved};
}
}

GuidedSessionView::GuidedSessionView() {
    setComponentID("guided");
    heading_.setText(juce::String::fromUTF8("GUIDED — TIMED LOCAL SESSION"), juce::dontSendNotification);
    heading_.setFont(juce::FontOptions{30.0f, juce::Font::bold});
    heading_.setColour(juce::Label::textColourId, appearance::colour(0xff6bd5cb));
    heading_.setComponentID("guided-heading");
    heading_.setTitle("Guided Session planner and linked Practice-summary path.");
    explanation_.setComponentID("guided-explanation");
    explanation_.setTitle("Read-only Guided Session entry, duration contract and linked Practice-summary path.");
    explanation_.setText(fullGuidedExplanation, juce::dontSendNotification);
    explanation_.setDescription(fullGuidedExplanation);
    explanation_.setHelpText(fullGuidedExplanation);
    explanation_.setTooltip(fullGuidedExplanation);
    explanation_.setFont(juce::FontOptions{16.0f});
    explanation_.setJustificationType(juce::Justification::topLeft);
    durationLabel_.setText("Duration", juce::dontSendNotification);
    durationLabel_.setComponentID("guided-duration-label");
    durationLabel_.setTitle("Guided duration presets: 10, 20, 30, 45 or 60 minutes.");
    customLabel_.setText("Custom minutes", juce::dontSendNotification);
    customLabel_.setComponentID("guided-custom-label");
    customLabel_.setTitle("Custom Guided duration in whole minutes from 1 to 240.");
    elapsedLabel_.setText("Elapsed 00:00:00", juce::dontSendNotification);
    elapsedLabel_.setComponentID("guided-elapsed");
    elapsedLabel_.setTitle("Elapsed Guided Session time; the active Session remains separate from Practice Attempt and curriculum progress.");
    elapsedLabel_.setFont(juce::FontOptions{18.0f, juce::Font::bold});
    status_.setFont(juce::FontOptions{15.0f});
    status_.setComponentID("guided-status");
    status_.setTitle("Read-only Guided Session lifecycle, next action and save boundary.");
    status_.setColour(juce::Label::textColourId, appearance::colour(0xffa9bbc5));
    status_.setJustificationType(juce::Justification::topLeft);
    status_.setText("Opening Guided does not start sound or create a Session. Choose a duration and build a source-backed plan. Next action: choose a duration, then choose Build Guided plan.", juce::dontSendNotification);
    summaryHeading_.setComponentID("guided-session-summary-heading");
    summaryHeading_.setTitle("Read-only Guided Session summary heading");
    summaryHeading_.setText("SESSION SUMMARY", juce::dontSendNotification);
    summaryHeading_.setFont(juce::FontOptions{14.0f, juce::Font::bold});
    summaryHeading_.setColour(juce::Label::textColourId, appearance::colour(0xff6bd5cb));
    summaryState_.setComponentID("guided-summary-state");
    summaryState_.setTitle("Guided summary empty-state marker.");
    summaryState_.setFont(juce::FontOptions{15.0f, juce::Font::bold});
    summaryState_.setColour(juce::Label::textColourId, appearance::colour(0xffa9bbc5));
    summaryState_.setText("No saved Guided Session yet", juce::dontSendNotification);
    sessionSummary_.setComponentID("session-summary");
    sessionSummary_.setTitle("Read-only Guided Session summary: Session identity, planned duration, elapsed time, outcome and linked Attempt facts.");
    sessionSummary_.setFont(juce::FontOptions{15.0f});
    sessionSummary_.setColour(juce::Label::textColourId, appearance::colour(0xffd8e7eb));
    sessionSummary_.setJustificationType(juce::Justification::topLeft);
    sessionSummary_.setText("Opening Guided summary does not create activity. Session summary: no Guided Session has been saved. Start creates one local Guided Session; no saved outcome exists yet.", juce::dontSendNotification);

    duration_.setComponentID("duration");
    duration_.addItem("10 minutes", 1); duration_.addItem("20 minutes", 2); duration_.addItem("30 minutes", 3);
    duration_.addItem("45 minutes", 4); duration_.addItem("60 minutes", 5); duration_.addItem("Custom duration", 6);
    duration_.setSelectedId(1, juce::dontSendNotification);
    duration_.onChange = [this] { buildPlan(); };
    custom_.setComponentID("custom");
    custom_.setEditableText(true); custom_.setText("15", juce::dontSendNotification);
    custom_.setTitle("Custom duration in minutes (1 to 240)");
    custom_.onChange = [this] { if (duration_.getSelectedId() == 6) buildPlan(); };

    plan_.setComponentID("plan"); plan_.setTitle("Source-backed Guided plan: runtime-admitted cases only; refused cases remain out of Practice.");
    plan_.setMultiLine(true); plan_.setReadOnly(true); plan_.setScrollbarsShown(true);
    plan_.setFont(juce::FontOptions{16.0f});
    plan_.setColour(juce::TextEditor::backgroundColourId, appearance::colour(0xff142b38));
    plan_.setColour(juce::TextEditor::textColourId, appearance::colour(0xffe1edf0));
    planState_.setComponentID("guided-plan-state");
    planState_.setTitle("Guided source-plan empty-state marker.");
    planState_.setFont(juce::FontOptions{15.0f, juce::Font::bold});
    planState_.setColour(juce::Label::textColourId, appearance::colour(0xffa9bbc5));
    planState_.setText("No source-backed Guided plan built yet", juce::dontSendNotification);

    for (auto* component : {static_cast<juce::Component*>(&heading_), static_cast<juce::Component*>(&explanation_),
                            static_cast<juce::Component*>(&durationLabel_), static_cast<juce::Component*>(&customLabel_),
                            static_cast<juce::Component*>(&elapsedLabel_), static_cast<juce::Component*>(&status_),
                            static_cast<juce::Component*>(&summaryHeading_),
                            static_cast<juce::Component*>(&summaryState_),
                            static_cast<juce::Component*>(&sessionSummary_),
                            static_cast<juce::Component*>(&planState_),
                            static_cast<juce::Component*>(&duration_), static_cast<juce::Component*>(&custom_),
                            static_cast<juce::Component*>(&plan_), static_cast<juce::Component*>(&audio_), static_cast<juce::Component*>(&build_), static_cast<juce::Component*>(&open_),
                            static_cast<juce::Component*>(&start_), static_cast<juce::Component*>(&stop_), static_cast<juce::Component*>(&interrupt_),
                            static_cast<juce::Component*>(&progress_), static_cast<juce::Component*>(&back_)}) addAndMakeVisible(*component);
    audio_.setComponentID("guided-audio-settings"); build_.setComponentID("build"); open_.setComponentID("open-first"); start_.setComponentID("start"); stop_.setComponentID("stop"); interrupt_.setComponentID("interrupt"); progress_.setComponentID("open-progress"); back_.setComponentID("back");
    auto configureControl=[&](juce::Component& component,const char* title,int order){component.setTitle(title);component.setWantsKeyboardFocus(true);component.setExplicitFocusOrder(order);};
    configureControl(audio_,"Open shared Audio settings without changing Guided Session state.",1); audio_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); audio_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); audio_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(duration_,"Choose Guided duration: 10, 20, 30, 45 or 60 minutes, or Custom.",2);
    configureControl(custom_,"Enter a whole custom Guided duration from 1 to 240 minutes.",3);
    configureControl(build_,"Build a source-backed Guided plan from the retained records.",4); build_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); build_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); build_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(open_,"Open the admitted source-backed case in Learn.",5); open_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); open_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); open_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(start_,"Start one local Guided Session; no Attempt or curriculum credit is created.",6); start_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); start_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); start_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(stop_,"Stop Guided and save its local Session outcome.",7); stop_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); stop_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); stop_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(interrupt_,"Interrupt Guided and leave the original Session unresolved.",8); interrupt_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); interrupt_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); interrupt_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(progress_,"Review saved Guided activity in Progress read-only.",9); progress_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); progress_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); progress_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    configureControl(back_,"Return to Home when the Guided Session is not active or unresolved.",10); back_.setColour(juce::TextButton::buttonColourId,appearance::colour(0xff6bd5cb)); back_.setColour(juce::TextButton::textColourOffId,appearance::colour(0xff10212c)); back_.setColour(juce::TextButton::textColourOnId,appearance::colour(0xff10212c));
    for(auto* action:{&audio_,&build_,&open_,&start_,&stop_,&interrupt_,&progress_,&back_})action->addKeyListener(this);
    build_.onClick = [this] { buildPlan(); }; open_.onClick = [this] { openFirstLesson(); };
    start_.onClick = [this] {
        if(createUnresolved_){if(createRetryAllowed_)retryOriginalStart();else inspectOriginalStart();}
        else startSession();
    };
    audio_.onClick = [this] {
        if (onAudioSettings) {
            onAudioSettings();
            return;
        }
        status_.setText("Audio settings are unavailable from Guided until the existing shared Audio page is connected. Return to Home and choose Audio settings; no Guided Session or sound was started.", juce::dontSendNotification);
        refreshControls();
    };
    stop_.onClick = [this] { stopSession(); }; interrupt_.onClick = [this] { interruptSession(); }; interrupt_.setButtonText("Interrupt & leave unresolved"); progress_.onClick = [this] { requestProgressPage(); }; back_.onClick = [this] { requestBack(); };
    startTimer(50); refreshControls();
}

GuidedSessionView::~GuidedSessionView() { stopTimer(); }

bool GuidedSessionView::configureStore(storage::ProfileStore& store, Clock utc, std::string zone) {
    if (busy() || running_ || createUnresolved_ || closeUnresolved_ || !utc || zone.empty()) return false;
    storage::validateUtc(utc()); storage::localDay(utc(), zone);
    store_ = &store; utcNow_ = std::move(utc); timezone_ = std::move(zone); unresolved_ = false; closeUnresolved_ = false; savedAttemptLinked_ = false; savedAttemptDetails_.clear();
    sessionId_.clear();closed_=false;restoredOriginal_=false;lastElapsedSeconds_=0;
    originalCreate_.reset();originalCloseOperation_.clear();originalCloseUtc_.clear();outcome_.clear();
    try {
        future_.emplace(store_->snapshot("guided-session/summary/" + storage::newUuid()));
        mutation_ = Mutation::LoadSummary;
        status_.setText("Loading the last saved Guided Session summary...", juce::dontSendNotification);
        sessionSummary_.setText("Session summary: loading saved Guided Session history...", juce::dontSendNotification);
        refreshControls(); return true;
    } catch (const std::exception& error) {
        summaryUnavailable_=true;
        setError(std::string("Guided Session summary could not be loaded: ") + error.what()); return false;
    }
}

void GuidedSessionView::setCatalog(std::shared_ptr<const lesson::Catalog> catalog) {
    if (running_ || (busy() && mutation_ != Mutation::LoadSummary)) return;
    catalog_ = std::move(catalog); if (!busy()) buildPlan();
}
void GuidedSessionView::setCatalogLoading(bool loading,const std::string& message) {
    catalogLoading_=loading;
    catalogLoadingMessage_=message;
    if(loading&&catalogFeedbackCanReplaceStatus()) {
        status_.setText(juce::String::fromUTF8(catalogLoadingFeedback().c_str()),juce::dontSendNotification);
    }
    refreshControls();
}

std::string GuidedSessionView::catalogLoadingFeedback() const {
    return catalogLoadingMessage_.empty()
        ? "Practice catalog is preparing. Wait for it to finish, or return Home; no new Guided plan is available while preparation is pending."
        : catalogLoadingMessage_;
}

bool GuidedSessionView::catalogFeedbackCanReplaceStatus() const {
    return !busy()&&!running_&&!unresolved_&&!closeUnresolved_&&!createUnresolved_&&!closed_&&!summaryUnavailable_;
}

bool GuidedSessionView::selectCase(const std::string& item, const std::string& variant) {
    if(!newSessionsEnabled_)return false;
    if (running_ || createUnresolved_ || (busy() && mutation_ != Mutation::LoadSummary)) return false;
    selectedItemId_ = item; selectedVariantId_ = variant;
    planValue_ = {};
    return busy() || buildPlan();
}

bool GuidedSessionView::openFirstLesson() {
    if(!newSessionsEnabled_)return false;
    if (catalogLoading_ || busy() || firstItemId_.empty() || firstVariantId_.empty()) return false;
    if (!onOpenLesson) {
        status_.setText("Learn is unavailable from Guided until the existing Learn page is connected. Return to Home and choose Learn to open the retained admitted source-backed case; no Practice activity or source case was opened.", juce::dontSendNotification);
        refreshControls();
        return false;
    }
    if (!onOpenLesson(firstItemId_, firstVariantId_)) {
        status_.setText("The first practice-ready source-backed case could not be opened in Learn. Return to Learn to choose an admitted source-backed case manually; no replacement case was loaded.", juce::dontSendNotification);
        refreshControls();
        return false;
    }
    std::string handoffStatus = (running_?"Stopped Practice prepared with admitted ":"Learn opened with admitted ") + firstItemId_ + " / " + firstVariantId_ + ". No Attempt, sound or practice credit was started by this preparation.";
    try {
        if (catalog_) {
            const auto admission = catalog_->admit(firstItemId_, firstVariantId_);
            if (admission && admission->practiceAllowed()) {
                const auto& identity = admission->identity().object();
                const auto& sourceRefs = admission->model()->source().sourceRefs;
                if (!sourceRefs.empty()) {
                    handoffStatus += "\nSource refs: ";
                    for (std::size_t index = 0; index < sourceRefs.size(); ++index) {
                        if (index != 0) handoffStatus += ", ";
                        handoffStatus += sourceRefs[index];
                    }
                }
                handoffStatus += "\nContent version: " + identity.at("content_version").string();
                handoffStatus += "\nContent revision: " + storage::canonical(identity.at("content_revision"));
                const auto& record = catalog_->lesson(firstItemId_).record.object();
                handoffStatus += "\nLesson title: " + record.at("title").string();
                handoffStatus += "\nVariant label: " + catalog_->variant(firstItemId_, firstVariantId_).label;
                handoffStatus += "\nWorkbook identity: " + record.at("workbook_id").string();
                handoffStatus += " | Level: " + storage::canonical(record.at("legacy_level"));
            }
        }
    } catch (const std::exception&) {
        // Preserve the r374 identity/no-credit status if provenance cannot be read.
    }
    status_.setText(handoffStatus, juce::dontSendNotification);
    refreshControls();
    return true;
}

bool GuidedSessionView::readDuration(int& minutes, std::string& error) const {
    const auto id = duration_.getSelectedId();
    if (id >= 1 && id <= 5) { minutes = presets[static_cast<std::size_t>(id - 1)]; return true; }
    if (id != 6) { error = "Choose a supported guided-session duration."; return false; }
    const auto text = utf8(custom_.getText().trim());
    if (text.empty()) { error = "Enter a whole custom duration from 1 to 240 minutes."; return false; }
    if (!std::all_of(text.begin(), text.end(), [](unsigned char c) { return c >= '0' && c <= '9'; })) {
        error = "Custom duration must be a whole number from 1 to 240 minutes."; return false;
    }
    std::int64_t value{}; const auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    if (parsed.ec != std::errc{} || parsed.ptr != text.data() + text.size() || value < 1 || value > 240) {
        error = "Custom duration must be between 1 and 240 minutes."; return false;
    }
    minutes = static_cast<int>(value); return true;
}

void GuidedSessionView::setError(const std::string& message) {
    status_.setText(juce::String::fromUTF8(message.c_str()), juce::dontSendNotification); refreshControls();
}

bool GuidedSessionView::buildPlan() {
    if(!newSessionsEnabled_)return false;
    if (catalogLoading_) {
        if(catalogFeedbackCanReplaceStatus())setError(catalogLoadingFeedback());
        else refreshControls();
        return false;
    }
    if (busy() || running_ || createUnresolved_) return false;
    int minutes{}; std::string error;
    if (!readDuration(minutes, error)) { planValue_ = {}; plan_.clear(); selectedMinutes_ = 0; setError(error + " Next action: correct the duration, then choose Build Guided plan."); return false; }
    if (!catalog_ || catalog_->lessons().empty()) {
        planValue_ = {}; plan_.setText("The local Development Preview catalog is unavailable. Open Learn to load the bundled source records, return here and choose Build plan; or rebuild this preview with its bundled source records.", false);
        selectedMinutes_ = 0; setError("No source-backed catalog is loaded; no guided plan was fabricated. Open Learn to load the bundled source records, then choose Build plan."); return false;
    }
    selectedMinutes_ = minutes; plannedSeconds_ = static_cast<std::int64_t>(minutes) * 60;
    firstItemId_.clear();
    firstVariantId_.clear();
    if (!selectedItemId_.empty()) {
        try {
            const auto admission = catalog_->admit(selectedItemId_, selectedVariantId_);
            if (!admission || !admission->practiceAllowed()) throw std::runtime_error("Selected case is not admitted");
            firstItemId_ = selectedItemId_; firstVariantId_ = selectedVariantId_;
            const auto& item = catalog_->lesson(firstItemId_);
            const auto& identity = admission->identity();
            planValue_ = V::Object{{"version", "guided-session-plan.1"}, {"duration_minutes", V::fromInteger(minutes)},
                {"planned_seconds", V::fromInteger(plannedSeconds_)}, {"content_version", catalog_->contentVersion(firstItemId_)},
                {"items", V::Array{planItem(item)}}, {"selected_case", identity}};
            std::ostringstream text;
            text << "GUIDED PLAN\nSelected single source-backed case: " << item.title << "\n"
                 << firstItemId_ << " / " << firstVariantId_ << " | " << catalog_->variant(firstItemId_, firstVariantId_).label
                 << "\nContent version: " << catalog_->contentVersion(firstItemId_)
                 << " | Revision: " << storage::canonical(identity.object().at("content_revision"))
                 << "\nSource refs: " << storage::canonical(identity.object().at("source_refs"))
                 << "\nDuration: " << minutes << " minutes (local Session budget; no authored BPM or cell pause)."
                 << "\nStart records this exact admitted identity in the local Session. Practice Start remains explicit."
                 << "\nNo Attempt, mastery or curriculum credit is created by planning or navigation.";
            plan_.setText(text.str(), false);
            status_.setText("Selected-case plan ready. Start creates one local Guided Session; no curriculum credit.", juce::dontSendNotification);
            refreshControls(); return true;
        } catch (const std::exception& error) {
            planValue_ = {}; plan_.clear(); firstItemId_.clear(); firstVariantId_.clear();
            selectedMinutes_ = 0; setError(std::string("Selected source case refused: ") + error.what()); return false;
        }
    }
    for (const auto& lesson : catalog_->lessons()) {
        bool practiceReady = false;
        for (const auto& variant : lesson.variants) {
            try {
                const auto admission = catalog_->admit(lesson.id, variant.id);
                if (admission && admission->practiceAllowed()) {
                    firstItemId_ = lesson.id;
                    firstVariantId_ = variant.id;
                    practiceReady = true;
                    break;
                }
            } catch (const std::exception&) {
                // Preserve the existing admission gate: a refused or malformed
                // variant cannot become a hidden Learn-to-Practice fallback.
            }
        }
        if (practiceReady) {
            break;
        }
    }
    const auto count = std::min<std::size_t>(3, catalog_->lessons().size());
    std::set<std::string> workbooks;
    for (const auto& lesson : catalog_->lessons())
        workbooks.insert(lesson.record.object().at("workbook_id").string());
    const auto remainingWorkbooks = workbooks.size() < 105 ? 105 - workbooks.size() : 0;
    const auto additionalWorkbooks = workbooks.size() > 13 ? workbooks.size() - 13 : 0;
    std::string firstSourceRefs;
    std::string firstLessonDetails;
    if (!firstItemId_.empty() && !firstVariantId_.empty()) {
        const auto& firstLesson = catalog_->lesson(firstItemId_);
        const auto& refs = catalog_->variant(firstItemId_, firstVariantId_).model->source().sourceRefs;
        for (std::size_t index = 0; index < refs.size(); ++index) {
            if (index != 0) firstSourceRefs += ", ";
            firstSourceRefs += refs[index];
        }
        firstLessonDetails = " | Lesson: " + firstLesson.title + " | Content revision: " + storage::canonical(firstLesson.record.object().at("content_revision")) +
            " | Workbook: " + firstLesson.record.object().at("workbook_id").string() + " | Level: " + storage::canonical(firstLesson.record.object().at("legacy_level"));
    }
    V::Array items; std::ostringstream text;
    text << "GUIDED PLAN\nDevelopment Preview; source-backed selected cases only.\nDuration: " << minutes
         << " minutes | planned local Session: " << plannedSeconds_ << " seconds\nPlan feasibility: one local Guided Session uses the selected whole-minute budget; this Development Preview does not allocate time per case.\nContent version: " << catalog_->contentVersion()
         << "\nPlan preview: showing " << count << " of " << catalog_->lessons().size() << " retained source-backed cases."
         << "\nMigration: " << workbooks.size() << " of 105 approved workbook identities packaged; " << remainingWorkbooks
         << " remain outside this Development Preview | Additional workbook identities represented by selected cases: " << additionalWorkbooks
         << " | Whole-workbook completion from these cases: 0 | Curriculum review: Pending"
         << (firstItemId_.empty() || firstVariantId_.empty()
                 ? "\nPractice handoff: unavailable; the existing runtime gate refused all retained variants."
                 : "\nPractice handoff: first practice-ready case in Learn is " + firstItemId_ + " / " + firstVariantId_ + " | Variant label: " + catalog_->variant(firstItemId_, firstVariantId_).label + (firstSourceRefs.empty() ? std::string{} : " | Source refs: " + firstSourceRefs) + firstLessonDetails + ".")
         << "\nNo workbook completion, Attempt, mastery or curriculum progress is inferred.\n\n";
    for (std::size_t i = 0; i < count; ++i) {
        const auto& item = catalog_->lessons()[i];
        items.emplace_back(planItem(item));
        text << i + 1 << ". Level " << item.level << " — " << item.title << " [" << item.id << "] | Variants available: " << item.variants.size();
        text << " | Revision: " << storage::canonical(item.record.object().at("content_revision"));
        text << " | Workbook: " << item.record.object().at("workbook_id").string()
             << " | Level: " << storage::canonical(item.record.object().at("legacy_level"));
        if (const auto* refs = item.record.find("source_refs"); refs && refs->isArray() && !refs->array().empty()) {
            text << " | Source: ";
            for (std::size_t ref = 0; ref < refs->array().size(); ++ref) {
                if (ref != 0) text << ", ";
                text << refs->array()[ref].string();
            }
        }
        text << admissionDisclosure(*catalog_, item);
        text << '\n';
    }
    planValue_ = V::Object{{"version", "guided-session-plan.1"}, {"duration_minutes", V::fromInteger(minutes)},
                           {"planned_seconds", V::fromInteger(plannedSeconds_)}, {"content_version", catalog_->contentVersion()}, {"items", items}};
    plan_.setText(juce::String::fromUTF8(text.str().c_str()), false);
    status_.setText("Plan ready. Start creates one local Guided Session from the retained source records; no curriculum credit is created.", juce::dontSendNotification);
    refreshControls(); return true;
}

bool GuidedSessionView::startSession() {
    if(!newSessionsEnabled_)return false;
    if (catalogLoading_ || busy() || running_ || unresolved_ || createUnresolved_ || !store_ || !utcNow_) return false;
    if (planValue_.null() && !buildPlan()) return false;
    if (planValue_.null()) return false;
    try {
        closeUnresolved_ = false;
        CreateRequest request;
        request.operation="guided-session/create/"+storage::newUuid();request.reservedOwner=storage::newUuid();request.utc=utcNow_();
        request.timezone=timezone_;request.seconds=plannedSeconds_;request.plan=planValue_;
        request.plan.object().emplace("original_start_operation",request.operation);
        request.plan.object().emplace("original_session_id",request.reservedOwner);
        restoredOriginal_=false;
        originalCreate_=std::move(request);createUnresolved_=true;createRetryAllowed_=false;
        const auto& original=*originalCreate_;
        future_.emplace(store_->createSessionWithIdentity(original.operation,original.reservedOwner,original.utc,original.timezone,original.seconds,original.plan));
        mutation_ = Mutation::Create;
        status_.setText("Creating local guided Session...", juce::dontSendNotification);
        sessionSummary_.setText("Session summary: creating a local Guided Session...", juce::dontSendNotification);
        refreshControls(); return true;
    } catch (const std::exception& error) { setError(std::string("Guided Session could not start: ") + error.what()); return false; }
}

bool GuidedSessionView::retryOriginalStart() {
    if(busy()||running_||!store_||!createUnresolved_||!createRetryAllowed_||!originalCreate_||!originalCreate_->owner.empty())return false;
    try {
        const auto& original=*originalCreate_;
        future_.emplace(store_->createSessionWithIdentity(original.operation,original.reservedOwner,original.utc,original.timezone,original.seconds,original.plan));
        mutation_=Mutation::Create;createRetryAllowed_=false;
        status_.setText("Retrying the unchanged original Guided start after its definite failure. Quit remains held until its identity is confirmed.",juce::dontSendNotification);
        refreshControls();return true;
    }catch(const std::exception& error){setError(std::string("Original Guided start retry could not begin: ")+error.what());return false;}
}

bool GuidedSessionView::inspectOriginalStart() {
    if(busy()||running_||!store_||!createUnresolved_||!originalCreate_||(originalCreate_->owner.empty()&&originalCreate_->reservedOwner.empty()))return false;
    try {
        future_.emplace(store_->snapshot(originalCreate_->operation+".inspect/"+storage::newUuid()));
        mutation_=Mutation::InspectCreate;
        status_.setText("Checking the original Guided Session in storage. No replacement Session is created; Quit remains held.",juce::dontSendNotification);
        refreshControls();return true;
    }catch(const std::exception& error){setError(std::string("Original Guided start inspection could not begin: ")+error.what());return false;}
}

void GuidedSessionView::adoptOriginalStart() {
    const auto& original=*originalCreate_;
    sessionId_=original.owner;plannedSeconds_=original.seconds;
    createUnresolved_=false;createRetryAllowed_=false;restoredOriginal_=false;savedAttemptLinked_=false;savedAttemptDetails_.clear();
    startedSteady_=std::chrono::steady_clock::now();running_=true;closed_=false;unresolved_=false;closeUnresolved_=false;originalCloseOperation_.clear();originalCloseUtc_.clear();exitStopAttempted_=false;
    elapsedLabel_.setText("Elapsed 00:00:00",juce::dontSendNotification);
    sessionSummary_.setText(juce::String::fromUTF8(("Session summary: active local Session "+sessionId_+
        "\n"+plannedDurationText(plannedSeconds_)+"\nNo curriculum progress is created.\nStop saves this same Session; an unresolved close stays retryable.\nThis active Guided Session owns any Practice Attempt saved from it.").c_str()),juce::dontSendNotification);
    status_.setText("Guided Session running locally. Save a Practice result before Guided summary becomes available. Stop saves this Session; no curriculum progress is created. Choose Prepare selected case in Practice; it opens stopped. Explicit Practice Start creates the Attempt. Save its result, then choose Guided summary to return to this original Session.",juce::dontSendNotification);
}

bool GuidedSessionView::stopSession() {
    if (busy() || closed_ || (!running_&&!restoredOriginal_) || !store_ || !utcNow_ || sessionId_.empty()) return false;
    try {
        if(originalCloseOperation_.empty()){
            if(restoredOriginal_){lastElapsedSeconds_=0;outcome_="interrupted";}
            else{lastElapsedSeconds_ = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - startedSteady_).count();
            outcome_ = lastElapsedSeconds_ >= plannedSeconds_ ? "complete" : "partial";}
            originalCloseUtc_=utcNow_();originalCloseOperation_="guided-session/close/"+storage::newUuid();
        }
        closeUnresolved_ = false;
        future_.emplace(store_->closeSession(originalCloseOperation_, sessionId_, originalCloseUtc_, outcome_));
        mutation_ = Mutation::Close;
        status_.setText("Saving the local guided Session...", juce::dontSendNotification);
        sessionSummary_.setText("Session summary: saving the Guided Session outcome...", juce::dontSendNotification);
        refreshControls(); return true;
    } catch (const std::exception& error) { setError(std::string("Guided Session close could not begin: ") + error.what()); return false; }
}

bool GuidedSessionView::interruptSession() {
    if (busy() || !running_ || !store_ || sessionId_.empty()) return false;
    lastElapsedSeconds_ = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::steady_clock::now() - startedSteady_).count();
    running_ = false; closed_ = false; unresolved_ = true; closeUnresolved_ = false;
    elapsedLabel_.setText(juce::String::fromUTF8(("Elapsed "+formatElapsed(std::chrono::seconds(lastElapsedSeconds_))).c_str()), juce::dontSendNotification);
    sessionSummary_.setText(juce::String::fromUTF8(("Session summary: interrupted local Session " + sessionId_ + " before Stop\n" +
        plannedDurationText(plannedSeconds_) + savedAttemptText(savedAttemptLinked_, savedAttemptDetails_) +
        "\nNo saved outcome is claimed.\nNo curriculum progress was created.").c_str()), juce::dontSendNotification);
    status_.setText("Guided Session left unresolved before Stop. Back is safe now; the original Session remains unresolved. No saved outcome or curriculum progress was created.", juce::dontSendNotification);
    refreshControls(); return true;
}

void GuidedSessionView::noteSavedPracticeAttempt() {
    if (!running_ || sessionId_.empty()) return;
    savedAttemptLinked_ = true;
    savedAttemptDetails_.clear();
    status_.setText("Guided Session remains active. The saved Practice Attempt is linked to this Session; Stop is temporarily unavailable while the local summary refresh completes.", juce::dontSendNotification);
    sessionSummary_.setText(juce::String::fromUTF8(("Session summary: active local Session " + sessionId_ +
        "\n" + plannedDurationText(plannedSeconds_) + "\nElapsed: " + formatElapsed(std::chrono::steady_clock::now() - startedSteady_) + savedAttemptText(true, savedAttemptDetails_) + "\nNo curriculum progress was created.").c_str()), juce::dontSendNotification);
    if (store_) {
        try {
            future_.emplace(store_->snapshot("guided-session/attempt-summary/" + storage::newUuid()));
            mutation_ = Mutation::RefreshAttempt;
        } catch (const std::exception&) {}
    }
    refreshControls(); resized();
}

bool GuidedSessionView::requestBack() {
    if (!canLeave()) {
        const std::string nextAction = createUnresolved_
            ? (createRetryAllowed_?" Next action: choose Retry original start before leaving.":" Next action: choose Check original start before leaving; keep the original profile open.")
            : closeUnresolved_
            ? " Next action: choose Retry original Guided close to resolve this Session, then choose Back."
            : " Next action: choose Stop Guided session to save this Session, then choose Back.";
        status_.setText(juce::String::fromUTF8((std::string{"Finish or save the current guided Session before going Back."} + nextAction).c_str()), juce::dontSendNotification);
        return false;
    }
    if (!onBack) { status_.setText("Back is unavailable from Guided until the existing Home navigation is connected. No Guided Session or summary state was changed; use the existing Home navigation when connected. Next action: reconnect the existing Home navigation, then choose Back.", juce::dontSendNotification); refreshControls(); return false; }
    onBack(); return true;
}

bool GuidedSessionView::requestProgressPage() {
    if (busy() || running_ || unresolved_ || !closed_ || !canLeave()) {
        const std::string nextAction = running_
            ? (savedAttemptLinked_
                ? " Next action: choose Stop & save Guided summary, then choose Review Progress."
                : " Next action: choose Stop Guided session to save this Session, then choose Review Progress.")
            : busy()
                ? " Next action: wait for the current Guided operation to settle, then choose Review Progress."
                : unresolved_
                    ? " Next action: resolve the current Guided Session close, then choose Review Progress."
                    : " Next action: finish the current Guided Session before choosing Review Progress.";
        status_.setText(juce::String::fromUTF8((std::string{"Save or resolve the current Guided Session before opening Progress; no finalized Guided record is available yet."} + nextAction).c_str()), juce::dontSendNotification);
        refreshControls();
        return false;
    }
    if (!onProgressPage) {
        status_.setText("Progress is unavailable from Guided until the existing Progress page is connected. Return to Home and choose Progress to review saved local activity.", juce::dontSendNotification);
        refreshControls();
        return false;
    }
    onProgressPage();
    return true;
}

std::string GuidedSessionView::formatElapsed(const std::chrono::steady_clock::duration elapsed) {
    const auto seconds = std::chrono::duration_cast<std::chrono::seconds>(elapsed).count(); std::ostringstream out;
    out << std::setfill('0') << std::setw(2) << seconds / 3600 << ':' << std::setw(2) << (seconds / 60) % 60 << ':' << std::setw(2) << seconds % 60; return out.str();
}

void GuidedSessionView::service() {
    if (!future_ || future_->wait_for(std::chrono::seconds(0)) != std::future_status::ready) {
        if (running_) elapsedLabel_.setText(juce::String::fromUTF8(("Elapsed "+formatElapsed(std::chrono::steady_clock::now() - startedSteady_)).c_str()), juce::dontSendNotification);
        return;
    }
    const auto mutation = mutation_; const auto reply = future_->get(); future_.reset();
    if(mutation==Mutation::InspectCreate){
        try {
            if(reply.status!=storage::Status::Confirmed)throw std::runtime_error("Inspection unavailable: "+reply.code+" "+reply.message);
            if(!originalCreate_||(originalCreate_->owner.empty()&&originalCreate_->reservedOwner.empty()))throw std::runtime_error("Original Session identity is unavailable; retain this legacy request for support");
            if(originalCreate_->owner.empty())originalCreate_->owner=originalCreate_->reservedOwner;
            const auto* authority=reply.data.find("authoritative");
            const auto* sessions=authority?authority->find("session"):nullptr;
            const auto* closes=authority?authority->find("session_close"):nullptr;
            if(!sessions||!sessions->isArray()||!closes||!closes->isArray())throw std::runtime_error("Original Session tables are unavailable");
            const auto& original=*originalCreate_;const V* found=nullptr;
            for(const auto& row:sessions->array())if(row.isArray()&&row.array().size()==5&&row.array()[0]==V(original.owner)){
                if(found)throw std::runtime_error("Original Session identity appears more than once");found=&row;
            }
            if(!found){
                createUnresolved_=true;createRetryAllowed_=true;originalCreate_->owner.clear();
                status_.setText("The exact original Guided Session is confirmed absent. Retry original start retains its operation, Session identity, time and plan; no replacement is created.",juce::dontSendNotification);
                sessionSummary_.setText("Session summary: the original Guided start is absent; no saved outcome is claimed.",juce::dontSendNotification);
                refreshControls();return;
            }
            std::string planHex;constexpr char digits[]="0123456789abcdef";
            for(const char byte:storage::canonical(original.plan)){const auto c=static_cast<unsigned char>(byte);planHex+=digits[c>>4];planHex+=digits[c&15];}
            const auto& row=found->array();std::int64_t seconds{};
            const auto* blob=row[4].isObject()?row[4].find("blob_hex"):nullptr;
            if(row[1]!=V(original.utc)||row[2]!=V(original.timezone)||!row[3].integer(seconds)||seconds!=original.seconds
                ||!blob||*blob!=V(planHex))throw std::runtime_error("Original Session values differ from the retained start request");
            for(const auto& close:closes->array())if(close.isArray()&&!close.array().empty()&&close.array()[0]==V(original.owner))
                throw std::runtime_error("Original Session already has a close; inspect the profile's saved history before continuing");
            adoptOriginalStart();refreshControls();return;
        }catch(const std::exception& error){
            setError(std::string("Original Guided start remains unresolved: ")+error.what());return;
        }
    }
    if(mutation==Mutation::Create){
        if(!originalCreate_||reply.operation!=originalCreate_->operation){
            createUnresolved_=true;createRetryAllowed_=false;setError("Guided start reply does not match the retained original operation. Keep this profile open.");return;
        }
        originalCreate_->status=reply.status;originalCreate_->errorCode=reply.code;originalCreate_->errorDetail=reply.message;
        if(!reply.owner.empty())originalCreate_->owner=reply.owner;
        if(reply.status!=storage::Status::Confirmed||originalCreate_->owner.empty()){
            createUnresolved_=true;
            createRetryAllowed_=originalCreate_->owner.empty()&&(reply.status==storage::Status::DefiniteFailure||reply.status==storage::Status::Busy||reply.status==storage::Status::DefinitelyAbsent);
            const auto action=createRetryAllowed_?"Retry original start":(originalCreate_->owner.empty()&&originalCreate_->reservedOwner.empty())?"keep this profile open for original-operation recovery":"Check original start";
            status_.setText(juce::String::fromUTF8(("Guided Session start unresolved: "+reply.code+" "+reply.message+". Original request retained. Next action: "+action+"; no replacement Session or outcome is claimed.").c_str()),juce::dontSendNotification);
            sessionSummary_.setText("Session summary: original Guided start unresolved; no saved outcome is claimed.",juce::dontSendNotification);
            refreshControls();return;
        }
    }
    if (mutation == Mutation::RefreshAttempt) {
        if (reply.status == storage::Status::Confirmed) {
            try {
                const auto summary = readSnapshotSummary(reply.data);
                if (summary.unresolved && summary.unresolved->sessionId == sessionId_)
                    savedAttemptDetails_ = attemptDetailsText(summary.unresolved->savedAttemptIdentity, catalog_.get());
            } catch (const std::exception&) {}
        }
        sessionSummary_.setText(juce::String::fromUTF8(("Session summary: active local Session " + sessionId_ +
            "\n" + plannedDurationText(plannedSeconds_) + "\nElapsed: " + formatElapsed(std::chrono::steady_clock::now() - startedSteady_) + savedAttemptText(savedAttemptLinked_, savedAttemptDetails_) +
            "\nNo curriculum progress was created.").c_str()), juce::dontSendNotification);
        const auto linkedSourceDisclosure = savedAttemptDetails_.empty()
            ? std::string{}
            : "\nLinked saved Practice Attempt:" + savedAttemptDetails_;
        status_.setText(juce::String::fromUTF8((std::string{"Guided Session remains active. Next action: choose Stop & save Guided summary. The saved Practice Attempt is linked to this Session; Stop saves this Session and remains separate from curriculum progress."} + linkedSourceDisclosure).c_str()), juce::dontSendNotification);
        refreshControls(); return;
    }
    if (mutation == Mutation::LoadSummary) {
        unresolved_ = false;
        if (reply.status != storage::Status::Confirmed) {
            summaryUnavailable_=true;
            savedAttemptLinked_ = false;
            savedAttemptDetails_.clear();
            status_.setText(juce::String::fromUTF8(("Saved Guided summary unavailable: " + reply.code + ". No saved outcome is claimed.").c_str()), juce::dontSendNotification);
            sessionSummary_.setText("Session summary: saved Guided history is unavailable; no saved outcome is claimed.", juce::dontSendNotification);
        } else {
            try {
                const auto summary = readSnapshotSummary(reply.data);
                summaryUnavailable_=false;
                if (summary.unresolved) {
                    unresolved_ = true;closed_=false;running_=false;
                    sessionId_=summary.unresolved->sessionId;plannedSeconds_=summary.unresolved->plannedSeconds;
                    restoredOriginal_=summary.unresolved->validatedOriginal;
                    elapsedLabel_.setText("Active time unavailable after restart",juce::dontSendNotification);
                    savedAttemptLinked_ = summary.unresolved->savedAttemptLinked;
                    savedAttemptDetails_ = attemptDetailsText(summary.unresolved->savedAttemptIdentity, catalog_.get());
                    sessionSummary_.setText(juce::String::fromUTF8(("Session summary: unresolved local Session " + summary.unresolved->sessionId +
                        "\n" + plannedDurationText(summary.unresolved->plannedSeconds) +
                        (savedAttemptLinked_ ? savedAttemptText(summary.unresolved->savedAttemptIdentity, catalog_.get()) : "") +
                        "\nNo saved outcome is claimed.\nNo curriculum progress was created.").c_str()), juce::dontSendNotification);
                    status_.setText(restoredOriginal_?"An unfinished original Guided Session is retained. Close original Guided Session records an interrupted outcome for this exact Session. Active time after restart is unavailable; no offline time or curriculum credit is invented.":"An unfinished Session is retained, but its original Guided plan could not be validated. New Start and original close are disabled; keep this profile for support.", juce::dontSendNotification);
                } else if (!summary.saved) {
                    savedAttemptLinked_ = false;
                    savedAttemptDetails_.clear();
                    status_.setText("No closed Guided Session is saved in this local profile.", juce::dontSendNotification);
                    sessionSummary_.setText("Session summary: no Guided Session has been saved.", juce::dontSendNotification);
                } else {
                    closed_ = true;sessionId_=summary.saved->sessionId;restoredOriginal_=false;
                    elapsedLabel_.setText("Saved Session; reopened active time is unavailable",juce::dontSendNotification);
                    savedAttemptLinked_ = summary.saved->savedAttemptLinked;
                    savedAttemptDetails_ = attemptDetailsText(summary.saved->savedAttemptIdentity, catalog_.get());
                    sessionSummary_.setText(juce::String::fromUTF8(("Session summary: restored saved local Session " + summary.saved->sessionId +
                        "\n" + plannedDurationText(summary.saved->plannedSeconds) + "\nSession wall-clock span (not verified active time): " +
                        formatElapsed(std::chrono::seconds(summary.saved->elapsedSeconds)) + "\nOutcome: " + outcomeDisplayText(summary.saved->outcome) +
                        (savedAttemptLinked_ ? savedAttemptText(summary.saved->savedAttemptIdentity, catalog_.get()) : "") +
                        "\nNo curriculum progress was created.\nSaved Guided Session history is read-only; Start creates a new local Session.\nOpen Progress reviews this saved Guided Session read-only; Start creates a new local Session.\nNext action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session.").c_str()), juce::dontSendNotification);
                    const auto restoredSourceDisclosure = savedAttemptDetails_.empty()
                        ? std::string{}
                        : "\nLinked saved Practice Attempt:" + savedAttemptDetails_;
                    status_.setText(juce::String::fromUTF8(("The last saved Guided Session was restored for viewing. Start creates a new local Session. Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session." + restoredSourceDisclosure).c_str()), juce::dontSendNotification);
                }
            } catch (const std::exception& error) {
                summaryUnavailable_=true;
                savedAttemptLinked_ = false;
                savedAttemptDetails_.clear();
                status_.setText(juce::String::fromUTF8(("Saved Guided summary unavailable: " + std::string(error.what()) + ". No saved outcome is claimed.").c_str()), juce::dontSendNotification);
                sessionSummary_.setText("Session summary: saved Guided history is unavailable; no saved outcome is claimed.", juce::dontSendNotification);
            }
        }
        if (catalog_ && planValue_.null()) buildPlan();
        refreshControls(); return;
    }
    if (reply.status != storage::Status::Confirmed) {
        const auto message = mutation == Mutation::Close
            ? "Guided Session close unresolved: " + reply.code + ". The same Session remains active; retry the original close or inspect the profile. Next action: choose Retry original Guided close to resubmit the close for this same Session."
            : "Guided Session start failed: " + reply.code + ". No plan credit was created.";
        status_.setText(juce::String::fromUTF8(message.c_str()), juce::dontSendNotification);
        if (mutation == Mutation::Close) {
            closeUnresolved_ = true;
            sessionSummary_.setText(juce::String::fromUTF8(("Session summary: close unresolved. Session " + sessionId_ +
                (restoredOriginal_?" remains unresolved; retry its original close. Active time is unavailable.\n":" remains active; retry Stop.\n") + plannedDurationText(plannedSeconds_) +
                savedAttemptText(savedAttemptLinked_, savedAttemptDetails_) +
                "\nNo saved outcome is claimed.").c_str()), juce::dontSendNotification);
        } else {
            sessionSummary_.setText("Session summary: Guided Session start failed. No Guided Session was saved.", juce::dontSendNotification);
        }
        refreshControls(); return;
    }
    if (mutation == Mutation::Create) {
        adoptOriginalStart();
    } else {
        running_ = false; closed_ = true; unresolved_ = false; closeUnresolved_ = false;
        elapsedLabel_.setText(restoredOriginal_?juce::String{"Active time unavailable after restart"}:juce::String::fromUTF8(("Elapsed "+formatElapsed(std::chrono::seconds(lastElapsedSeconds_))).c_str()), juce::dontSendNotification);
        sessionSummary_.setText(juce::String::fromUTF8(("Session summary: saved local Session " + sessionId_ +
            "\n" + plannedDurationText(plannedSeconds_) + (restoredOriginal_?"\nActive time unavailable after restart; offline time is not credited.":"\nElapsed: "+formatElapsed(std::chrono::seconds(lastElapsedSeconds_))) + "\nOutcome: " + outcomeDisplayText(outcome_) +
            savedAttemptText(savedAttemptLinked_, savedAttemptDetails_) +
            "\nNo curriculum progress was created.").c_str()), juce::dontSendNotification);
        const auto linkedSourceDisclosure = savedAttemptDetails_.empty()
            ? std::string{}
            : "\nLinked saved Practice Attempt:" + savedAttemptDetails_;
        status_.setText(juce::String::fromUTF8(("Guided Session saved locally. Outcome: " + outcome_ + ". Back is safe now; Start creates a new local Session. It remains separate from curriculum progress. Next action: choose Review Progress (read-only) for a read-only activity review, or Start Guided session to begin a new local Session." + linkedSourceDisclosure).c_str()), juce::dontSendNotification);
    }
    refreshControls();
}

void GuidedSessionView::timerCallback() { service(); }

bool GuidedSessionView::keyPressed(const juce::KeyPress& key,juce::Component* source) {
    if(key.getKeyCode()!=juce::KeyPress::spaceKey||!isShowing())return false;
    auto* action=dynamic_cast<juce::TextButton*>(source);
    if(!action||!action->isShowing()||!action->isEnabled())return false;
    if(spaceHeld_)return true;
    spaceHeld_=true;
    action->triggerClick();
    return true;
}

bool GuidedSessionView::keyStateChanged(bool,juce::Component*) {
    if(!juce::KeyPress::isKeyCurrentlyDown(juce::KeyPress::spaceKey))spaceHeld_=false;
    return false;
}

void GuidedSessionView::refreshStopLabel() {
    stop_.setButtonText(closeUnresolved_ ? "Retry original Guided close"
        : restoredOriginal_&&!closed_ ? "Close original Guided Session"
        : running_ && savedAttemptLinked_ && !busy()
            ? ((getWidth() < 800 || getHeight() < 680) ? "Stop & save summary" : "Stop & save Guided summary")
            : "Stop Guided session");
}

void GuidedSessionView::refreshControls() {
    if(catalogLoading_&&planValue_.null()&&catalogFeedbackCanReplaceStatus()) {
        const auto feedback=juce::String::fromUTF8(catalogLoadingFeedback().c_str());
        if(plan_.getText()!=feedback)plan_.setText(feedback,false);
    }
    const bool editable = newSessionsEnabled_ && !busy() && !running_ && !createUnresolved_ && !catalogLoading_;
    const bool emptySummary = !busy() && sessionId_.empty() && !running_ && !closed_ && !unresolved_;
    summaryState_.setVisible(emptySummary);
    summaryState_.setText("No saved Guided Session yet", juce::dontSendNotification);
    planState_.setVisible(catalogLoading_||(!busy() && !running_ && planValue_.null()));
    planState_.setText(catalogLoading_?juce::String::fromUTF8(catalogLoadingFeedback().c_str()):juce::String{"No source-backed Guided plan built yet"}, juce::dontSendNotification);
    duration_.setEnabled(editable); custom_.setEnabled(editable && duration_.getSelectedId() == 6); build_.setButtonText("Build Guided plan"); build_.setEnabled(editable&&!catalogLoading_);
    open_.setButtonText(running_?"Prepare selected case in Practice":"Inspect selected case in Learn");
    std::string openTitle = firstItemId_.empty() || firstVariantId_.empty()
        ? std::string{"Open the admitted source-backed case in Learn."}
        : "Open admitted " + firstItemId_ + " / " + firstVariantId_ + " in Learn";
    if (!firstItemId_.empty() && !firstVariantId_.empty() && catalog_) {
        try { openTitle += ": " + catalog_->lesson(firstItemId_).title; }
        catch (const std::exception&) {}
        openTitle += ". Practice Start remains explicit and no curriculum credit is inferred.";
    }
    if(running_)openTitle="Prepare stopped Practice for "+firstItemId_+" / "+firstVariantId_+" under this original Guided Session. Explicit Practice Start and Save remain separate; saved summary returns to this Guided Session.";
    open_.setTitle(juce::String::fromUTF8(openTitle.c_str()));
    open_.setEnabled(newSessionsEnabled_ && !catalogLoading_ && !busy() && !firstItemId_.empty() && !firstVariantId_.empty());
    start_.setButtonText(createUnresolved_?(createRetryAllowed_?"Retry original start":"Check original start"):"Start Guided session");
    start_.setEnabled(createUnresolved_?(!busy()&&store_&&originalCreate_&&(createRetryAllowed_||!originalCreate_->owner.empty()||!originalCreate_->reservedOwner.empty())):newSessionsEnabled_&&editable&&store_&&!planValue_.null()&&!unresolved_);
    stop_.setEnabled(!closed_&&(running_||restoredOriginal_) && !busy()); refreshStopLabel(); stop_.setTitle(restoredOriginal_?"Close this exact restored original as interrupted; active time is unavailable and is not invented.":closeUnresolved_ ? "Retry the unresolved Guided close before returning to Home." : (running_ && savedAttemptLinked_ && !busy() ? "Stop Guided and save this Session with its linked Practice summary." : "Stop Guided and save its local Session outcome.")); interrupt_.setEnabled(running_ && !busy());
    const bool savedSummary = closed_ && !unresolved_ && canLeave();
    progress_.setButtonText(savedSummary ? "Review Progress (read-only)" : "Open Progress");
    std::string progressTitle = savedSummary
        ? "Open read-only Progress for saved Guided Session " + sessionId_
        : "Review saved Guided activity in Progress read-only.";
    if (savedSummary) progressTitle += savedAttemptLinked_
        ? " with its linked Practice Attempt; no new Session or Attempt is created."
        : "; no new Session or Attempt is created.";
    progress_.setTitle(juce::String::fromUTF8(progressTitle.c_str()));
    progress_.setVisible(savedSummary);
    progress_.setEnabled(savedSummary && static_cast<bool>(onProgressPage));
    std::string startTitle = savedSummary
        ? "Start a new local Guided Session; the saved Guided summary remains read-only."
        : "Start one local Guided Session; no Attempt or curriculum credit is created.";
    if (!savedSummary && !firstItemId_.empty() && !firstVariantId_.empty())
        startTitle = "Start one local Guided Session for " + firstItemId_ + " / " + firstVariantId_ + "; no Attempt or curriculum credit is created.";
    if(createUnresolved_)startTitle=createRetryAllowed_?"Retry only the unchanged original Guided start after its definite failure.":"Inspect the exact original Guided Session; never create a replacement for an ambiguous start.";
    start_.setTitle(juce::String::fromUTF8(startTitle.c_str()));
    audio_.setEnabled(true);
    back_.setTitle(closeUnresolved_
        ? "Resolve the unresolved Guided close before returning to Home."
        : running_
            ? "Finish and save the active Guided Session before returning to Home."
            : savedSummary
                ? ("Return to Home after saved Guided Session " + sessionId_ + (savedAttemptLinked_ ? "; linked Practice Attempt remains read-only." : "; no linked Practice Attempt is present."))
                : "Return to Home when the Guided Session is not active or unresolved.");
    back_.setEnabled(canLeave());
    // Session transitions can change the linked summary without a window resize.
    // Refresh its text and linked/unlinked layout only when that cue changes.
    const juce::String visibleExplanation = savedAttemptLinked_ ? linkedGuidedExplanation
        : (getWidth() < 800 || getHeight() < 680) ? compactGuidedExplanation : fullGuidedExplanation;
    if (explanation_.getText() != visibleExplanation) resized();
}

void GuidedSessionView::paint(juce::Graphics& graphics) { graphics.fillAll(appearance::colour(0xff10212c)); }

void GuidedSessionView::resized() {
    refreshStopLabel();
    const juce::String visibleExplanation = savedAttemptLinked_ ? linkedGuidedExplanation
        : (getWidth() < 800 || getHeight() < 680) ? compactGuidedExplanation : fullGuidedExplanation;
    if (explanation_.getText() != visibleExplanation)
        explanation_.setText(visibleExplanation, juce::dontSendNotification);
    if (getWidth() < 800 || getHeight() < 680) {
        if (heading_.getText().startsWith("GUIDED") && heading_.getText().contains("TIMED LOCAL SESSION")) heading_.setText(juce::String::fromUTF8("Guided — Timed local session"), juce::dontSendNotification);
        auto area = getLocalBounds().reduced(16); const int width = area.getWidth();
        auto headingArea = area.removeFromTop(34); audio_.setBounds(headingArea.removeFromRight(170)); heading_.setBounds(headingArea);
        area.removeFromTop(6); explanation_.setBounds(area.removeFromTop(savedAttemptLinked_ ? 72 : 96)); area.removeFromTop(6);
        auto controls = area.removeFromTop(34); durationLabel_.setBounds(controls.removeFromLeft(72)); duration_.setBounds(controls.removeFromLeft(170)); controls.removeFromLeft(8); customLabel_.setBounds(controls.removeFromLeft(104)); custom_.setBounds(controls.removeFromLeft(100)); build_.setBounds(controls.removeFromLeft(std::min(120,controls.getWidth())));
        area.removeFromTop(6); elapsedLabel_.setBounds(area.removeFromTop(26)); status_.setBounds(area.removeFromTop(savedAttemptLinked_ ? 86 : 66));
        area.removeFromTop(4); auto summaryHeader = area.removeFromTop(20); summaryHeading_.setBounds(summaryHeader.removeFromLeft(140)); summaryState_.setBounds(summaryHeader); area.removeFromTop(2); sessionSummary_.setBounds(area.removeFromTop(72)); area.removeFromTop(4);
        planState_.setBounds(area.removeFromTop(20)); area.removeFromTop(2);
        plan_.setBounds(area.removeFromTop(std::max(1,area.getHeight()-98)));
        auto firstRow = juce::Rectangle<int>{area.getX(),getHeight()-76,width,32}; start_.setBounds(firstRow.removeFromLeft(108)); firstRow.removeFromLeft(6); open_.setBounds(firstRow.removeFromLeft(200)); firstRow.removeFromLeft(6); stop_.setBounds(firstRow.removeFromLeft(150));
        auto secondRow = juce::Rectangle<int>{area.getX(),getHeight()-38,width,32}; interrupt_.setBounds(secondRow.removeFromLeft(150)); secondRow.removeFromLeft(6); progress_.setBounds(secondRow.removeFromLeft(150)); back_.setBounds(secondRow.removeFromRight(80));
        return;
    }
    if (heading_.getText().startsWith("Guided") && heading_.getText().contains("Timed local session")) heading_.setText(juce::String::fromUTF8("GUIDED — TIMED LOCAL SESSION"), juce::dontSendNotification);
    auto area = getLocalBounds().reduced(28); auto headingArea = area.removeFromTop(40); audio_.setBounds(headingArea.removeFromRight(170)); heading_.setBounds(headingArea); area.removeFromTop(8);
    const int explanationHeight = savedAttemptLinked_ ? 72 : 90;
    explanation_.setBounds(area.removeFromTop(explanationHeight)); area.removeFromTop(8);
    auto controls = area.removeFromTop(34); durationLabel_.setBounds(controls.removeFromLeft(72)); duration_.setBounds(controls.removeFromLeft(170));
    controls.removeFromLeft(14); customLabel_.setBounds(controls.removeFromLeft(116)); custom_.setBounds(controls.removeFromLeft(110)); build_.setBounds(controls.removeFromLeft(120));
    const int statusHeight=savedAttemptLinked_?120:84;
    area.removeFromTop(8); elapsedLabel_.setBounds(area.removeFromTop(30)); status_.setBounds(area.removeFromTop(statusHeight));
    area.removeFromTop(6); auto summaryHeader = area.removeFromTop(22); summaryHeading_.setBounds(summaryHeader.removeFromLeft(160)); summaryState_.setBounds(summaryHeader); area.removeFromTop(4); sessionSummary_.setBounds(area.removeFromTop(getHeight()<=700?(savedAttemptLinked_?100:120):160)); area.removeFromTop(8);
    planState_.setBounds(area.removeFromTop(22)); area.removeFromTop(4);
    auto buttons = area.removeFromBottom(36); plan_.setBounds(area.removeFromTop(std::max(1,area.getHeight())));
    start_.setBounds(buttons.removeFromLeft(135)); buttons.removeFromLeft(8); open_.setBounds(buttons.removeFromLeft(190)); buttons.removeFromLeft(8); stop_.setBounds(buttons.removeFromLeft(150)); buttons.removeFromLeft(8); interrupt_.setBounds(buttons.removeFromLeft(135)); buttons.removeFromLeft(8); progress_.setBounds(buttons.removeFromLeft(115)); buttons.removeFromLeft(8); back_.setBounds(buttons.removeFromRight(80));
}

} // namespace fathom::desktop
