#include "tasks/OrderedContactTask.hpp"
#include "tasks/ContactSnapshotValues.hpp"
#include "content/Canonical.hpp"
#include "tasks/SourceContactChoiceOperators.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include "content/StrictJson.hpp"
#include "GeneratedOrderedContactPolicy.hpp"
#include "GeneratedPhysicalContactPolicy.hpp"
#include <algorithm>
#include <atomic>
#include <limits>
#include <map>
#include <set>

namespace fathom::tasks::ordered_contacts::manual {
namespace {
using J = json::Value;
void need(bool good, const char* code) { if (!good) throw Refusal(code); }
const J& at(const J& obj, const char* name) {
    need(obj.isObject() && obj.find(name), "ORDERED_TASK_POLICY_FIELD"); return *obj.find(name);
}
int integer(const J& value) {
    std::int64_t n = 0;
    need(value.integer(n) && n >= 0 && n <= std::numeric_limits<int>::max(), "ORDERED_TASK_POLICY_INTEGER");
    return static_cast<int>(n);
}
template<class Enum> Enum named(const J& value, const std::map<std::string, Enum>& names) {
    need(value.isString() && names.count(value.string()), "ORDERED_TASK_POLICY_ENUM"); return names.at(value.string());
}
const std::map<std::string, Rhythm> rhythmNames{{"Unspecified", Rhythm::Unspecified}, {"StraightEighth", Rhythm::StraightEighth},
    {"StraightSixteenth", Rhythm::StraightSixteenth}, {"Triplet", Rhythm::Triplet}, {"Quintuplet", Rhythm::Quintuplet},
    {"SixteenthTriplet", Rhythm::SixteenthTriplet}, {"OneNotePerClick", Rhythm::OneNotePerClick}, {"SourceMetric",Rhythm::SourceMetric}};
const std::map<std::string, Pass> passNames{{"ConnectedEqual", Pass::ConnectedEqual}, {"LandingAccent", Pass::LandingAccent},
    {"SeparatedAccent", Pass::SeparatedAccent}, {"SeparatedEqual", Pass::SeparatedEqual},
    {"PausedEighthAccent", Pass::PausedEighthAccent}, {"StoppedRelocation", Pass::StoppedRelocation},
    {"ConnectedEighthAccent", Pass::ConnectedEighthAccent}, {"ConnectedEighthEqual", Pass::ConnectedEighthEqual},
    {"ConnectedSixteenth", Pass::ConnectedSixteenth}, {"SourceAccent", Pass::SourceAccent},
    {"SourceEqual", Pass::SourceEqual}, {"SourcePerformance", Pass::SourcePerformance}, {"SourceDisplacement", Pass::SourceDisplacement}};
const std::map<std::string, Extension> extensionNames{{"AlternatingModes", Extension::AlternatingModes},
    {"DistanceP5P8P11", Extension::DistanceP5P8P11}, {"DistanceP5P7P10", Extension::DistanceP5P7P10},
    {"OtherPositionDistance", Extension::OtherPositionDistance}};
template<class Enum> bool includes(const std::vector<Enum>& list, Enum value) {
    return std::find(list.begin(), list.end(), value) != list.end();
}
bool claim(Claim value) { return value == Claim::Unknown || value == Claim::No || value == Claim::Yes; }
void requireClaim(Claim value) { need(claim(value), "ORDERED_TASK_UNKNOWN_CLAIM"); }
bool specialPulse(Rhythm r) { return r == Rhythm::Triplet || r == Rhythm::Quintuplet; }
bool validDate(const std::string& value) {
    if (value.size() != 10 || value[4] != '-' || value[7] != '-') return false;
    for (std::size_t i = 0; i < value.size(); ++i)
        if (i != 4 && i != 7 && (value[i] < '0' || value[i] > '9')) return false;
    const int year = std::stoi(value.substr(0, 4)), month = std::stoi(value.substr(5, 2)), day = std::stoi(value.substr(8));
    if (year == 0 || month < 1 || month > 12) return false;
    const int lengths[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    const int leap = month == 2 && year % 4 == 0 && (year % 100 != 0 || year % 400 == 0) ? 1 : 0;
    return day >= 1 && day <= lengths[month - 1] + leap;
}
struct Policies {
    std::map<int, Policy> items;
    std::map<int, J> encoded;
    Policies() {
        for (const auto* raw : compiled::policies) {
            auto object = json::parse(raw);
            const auto& p = at(object, "policy"); const auto& context = at(object, "source_context");
            Policy v;
            v.level = integer(at(p, "level"));
            const auto& ref = at(p, "context_ref"); const auto& text = at(p, "source_text_ref");
            v.contextPath = at(ref, "path").string(); v.contextSha256 = at(ref, "sha256").string();
            v.sourceTextPath = at(text, "path").string(); v.sourceTextSha256 = at(text, "sha256").string();
            for (const auto& line : at(context, "guidance_lines").array())
                v.sourceLines.push_back({integer(at(line, "line")), at(line, "text").string()});
            for (const auto& option : at(p, "passes").array()) {
                PassOption choice{named(at(option, "pass"), passNames), {}, {},
                    at(option, "needs_reported_stable_landings").boolean()};
                for (const auto& r : at(option, "rhythms").array()) choice.rhythms.push_back(named(r, rhythmNames));
                for (const auto& line : at(option, "source_lines").array()) choice.sourceLines.push_back(integer(line));
                need(!choice.rhythms.empty() && !choice.sourceLines.empty(), "ORDERED_TASK_EMPTY_PASS");
                v.passes.push_back(std::move(choice));
            }
            v.previousLevel = integer(at(p, "previous_level"));
            v.belowCleanMinimum = integer(at(p, "below_clean_minimum"));
            v.belowCleanMaximum = integer(at(p, "below_clean_maximum"));
            v.slowerOfTwoPreviousModes = at(p, "slower_of_two_previous_modes").boolean();
            v.oneModePerSession = at(p, "one_mode_per_session").boolean();
            v.downStartFirst = at(p, "down_start_first").boolean();
            v.rotationAcrossSessions = at(p, "rotation_across_sessions").boolean();
            v.restoreAfterStable = at(p, "restore_after_stable").boolean();
            v.restoreAfterAdvancement = at(p, "restore_after_advancement").boolean();
            v.advancementNeedsTwoDays = at(p, "advancement_needs_two_days").boolean();
            v.advancementNeedsBothModes = at(p, "advancement_needs_both_modes").boolean();
            v.advancementNeedsBothStarts = at(p, "advancement_needs_both_starts").boolean();
            v.advancementNeedsBothRoutes = at(p, "advancement_needs_both_routes").boolean();
            for (const auto& e : at(p, "extensions").array()) v.extensions.push_back(named(e, extensionNames));
            need(v.level >= 2 && v.level <= 11 && !v.passes.empty() && items.emplace(v.level, v).second,
                 "ORDERED_TASK_POLICY_CLOSED_SCOPE");
            encoded.emplace(v.level, std::move(object));
        }
        need(items.size() == 10, "ORDERED_TASK_POLICY_DENOMINATOR");
    }
};
const Policies& policies() { static const Policies instance; return instance; }
std::atomic<std::uint64_t> nextOwner{1};
std::string name(Rhythm value) {
    for (const auto& entry : rhythmNames) if (entry.second == value) return entry.first;
    throw Refusal("ORDERED_TASK_UNKNOWN_RHYTHM");
}
std::string name(Pass value) {
    for (const auto& entry : passNames) if (entry.second == value) return entry.first;
    throw Refusal("ORDERED_TASK_UNKNOWN_PASS");
}
J number(const std::optional<int>& value) { return value ? J::fromInteger(*value) : J(nullptr); }
J reported(Claim value) {
    requireClaim(value); return J(value == Claim::Yes ? "Yes" : value == Claim::No ? "No" : "Unknown");
}
FieldDescriptor choiceField(FieldId id, const std::string& label, std::vector<ChoiceDescriptor> choices, bool required = true) {
    return {id, FieldKind::Choice, label, required, std::move(choices), {}, {}, {}};
}
FieldDescriptor reportField(FieldId id, const std::string& label, bool required = true) {
    return choiceField(id, label, {{Claim::Unknown, "Not reported"}, {Claim::No, "No"}, {Claim::Yes, "Yes"}}, required);
}
FieldDescriptor bpmField(FieldId id, const std::string& label) {
    return {id, FieldKind::PositiveInteger, label, false, {}, 1, {}, {}};
}
std::string label(Rhythm value) {
    switch (value) {
    case Rhythm::Unspecified: return "Untimed stop and relocation";
    case Rhythm::StraightEighth: return "Even eighth notes";
    case Rhythm::StraightSixteenth: return "Straight sixteenth notes";
    case Rhythm::Triplet: return "Existing triplet grouping";
    case Rhythm::Quintuplet: return "Existing quintuplet grouping";
    case Rhythm::SixteenthTriplet: return "Sixteenth-note triplets (sextuplets), manually";
    case Rhythm::OneNotePerClick: return "One note per chosen manual click";
    case Rhythm::SourceMetric: return "Original written hand slots, manually without a clock";
    }
    throw Refusal("ORDERED_TASK_UNKNOWN_RHYTHM");
}
std::string label(Pass value) {
    switch (value) {
    case Pass::ConnectedEqual: return "Connected route, equal notes";
    case Pass::LandingAccent: return "Light landing accents";
    case Pass::SeparatedAccent: return "Separate cells, light landing accents";
    case Pass::SeparatedEqual: return "Separate cells, equal notes";
    case Pass::PausedEighthAccent: return "Eighth notes with shift pauses and landing accents";
    case Pass::StoppedRelocation: return "Stop, release and relocate";
    case Pass::ConnectedEighthAccent: return "Connected eighths with landing accents";
    case Pass::ConnectedEighthEqual: return "Connected eighths, equal notes";
    case Pass::ConnectedSixteenth: return "Connected sixteenth notes";
    case Pass::SourceAccent: return "Learning pulse with printed group accents";
    case Pass::SourceEqual: return "Printed grouped pulse with equal notes";
    case Pass::SourcePerformance: return "Printed performance pulse with equal notes";
    case Pass::SourceDisplacement: return "Optional displacement after grouped pulse is secure";
    }
    throw Refusal("ORDERED_TASK_UNKNOWN_PASS");
}
}

const Policy& policy(int level) {
    need(policies().items.count(level), "ORDERED_TASK_UNKNOWN_LEVEL"); return policies().items.at(level);
}
const char* policyClosureSha256() { (void)policies(); return compiled::closureSha; }

namespace {
const std::map<std::string, SourceDuty> dutyNames{
    {"ScaleComparison",SourceDuty::ScaleComparison},{"EarNaming",SourceDuty::EarNaming},
    {"FirstOctave",SourceDuty::FirstOctave},{"AscendingHalf",SourceDuty::AscendingHalf},
    {"DescendingHalf",SourceDuty::DescendingHalf},{"AdjacentModules",SourceDuty::AdjacentModules},
    {"PausedCircuit",SourceDuty::PausedCircuit},{"AccentedCircuit",SourceDuty::AccentedCircuit},
    {"EqualCircuit",SourceDuty::EqualCircuit},{"GroupedSecure",SourceDuty::GroupedSecure},
    {"LinkedModules",SourceDuty::LinkedModules},{"NeighboringRungs",SourceDuty::NeighboringRungs},
    {"FullRoute",SourceDuty::FullRoute},{"ThreeCleanRoundTrips",SourceDuty::ThreeCleanRoundTrips},
    {"SourceMapNaming",SourceDuty::SourceMapNaming},{"UnselectedSourceBranches",SourceDuty::UnselectedSourceBranches},
    {"RootAccentThenRemove",SourceDuty::RootAccentThenRemove},{"ShortenedRouteRepair",SourceDuty::ShortenedRouteRepair},
    {"NoisePressureThumbRepair",SourceDuty::NoisePressureThumbRepair},{"LostKeyRootRepair",SourceDuty::LostKeyRootRepair},
    {"WrongPositionNamingRepair",SourceDuty::WrongPositionNamingRepair},{"EarlyShiftAnchorRepair",SourceDuty::EarlyShiftAnchorRepair},
    {"ExactCountAirPickingRepair",SourceDuty::ExactCountAirPickingRepair}};
struct PhysicalPolicies {
    std::map<int, Policy> items;
    std::map<int, J> encoded;
    PhysicalPolicies() {
        for (const auto* raw : physical_policy_data::policies) {
            auto object=json::parse(raw); Policy v{};
            v.level=integer(at(object,"level")); v.family=manual_contacts::Family::PhysicalContact;
            const auto& ref=at(object,"context_ref"); const auto& context=at(object,"source_context");
            const auto& txt=at(at(context,"originals"),"txt");
            v.contextPath=at(ref,"path").string(); v.contextSha256=at(ref,"sha256").string();
            v.sourceTextPath=at(txt,"path").string(); v.sourceTextSha256=at(txt,"sha256").string();
            for (const auto& line:at(context,"guidance_lines").array())
                v.sourceLines.push_back({integer(at(line,"line")),at(line,"text").string()});
            for (const auto& line:at(object,"safe_instruction_lines").array()) v.safeInstructionLines.push_back(integer(line));
            for (const auto& option:at(object,"passes").array()) {
                const auto& r=at(option,"rhythm");
                v.passes.push_back({named(at(option,"pass"),passNames),
                    r.string()=="row_grouped" ? std::vector<Rhythm>{} : std::vector<Rhythm>{named(r,rhythmNames)},
                    v.safeInstructionLines,false});
            }
            for (const auto& option:at(object,"duties").array()) {
                SourceDutyOption d{named(at(option,"id"),dutyNames),at(option,"label").string(),{},at(option,"needs_release").boolean()};
                for (const auto& line:at(option,"source_lines").array()) d.sourceLines.push_back(integer(line));
                need(!d.sourceLines.empty(),"PHYSICAL_TASK_DUTY_SOURCE_LINES");v.sourceDuties.push_back(std::move(d));
            }
            v.sourceTempoRule=at(object,"source_tempo_rule").boolean();
            v.previousLevel=integer(at(object,"previous_level"));
            v.belowCleanMinimum=integer(at(object,"below_clean_minimum"));v.belowCleanMaximum=integer(at(object,"below_clean_maximum"));
            v.approximateThreeQuarters=at(object,"approximate_three_quarters").boolean();
            v.advancementNeedsTwoDays=at(object,"two_separate_days").boolean();
            v.advancementNeedsBothStarts=v.advancementNeedsTwoDays;v.advancementNeedsBothRoutes=v.advancementNeedsTwoDays;
            v.groupedBeforeDisplacement=at(object,"grouped_before_displacement").boolean();
            v.minorGeometryRelease=at(object,"minor_geometry_release").boolean();v.upperGeometryRebuild=at(object,"upper_geometry_rebuild").boolean();v.sourceGeometryObservation=at(object,"source_geometry_observation").boolean();
            need(v.level>=16&&v.level<=33&&items.emplace(v.level,v).second,"PHYSICAL_TASK_EXACT_POLICY_TAG");
            encoded.emplace(v.level,std::move(object));
        }
        need(items.size()==18,"PHYSICAL_TASK_POLICY_DENOMINATOR");
    }
};
const PhysicalPolicies& physicalPolicies() { static const PhysicalPolicies instance;return instance; }
manual_contacts::Start neutral(Start start) { return start==Start::Down?manual_contacts::Start::Down:start==Start::Up?manual_contacts::Start::Up:manual_contacts::Start::Unspecified; }
bool physical(const Policy& p) { return p.family==manual_contacts::Family::PhysicalContact||p.family==manual_contacts::Family::PiecewiseContact; }
bool sourceContact(const Policy& p) {return p.family==manual_contacts::Family::SourceContact;}
bool harmonic(const Policy& p) {return p.family==manual_contacts::Family::HarmonicContact||sourceContact(p);}
bool piecewise(const Policy& p) {return p.family==manual_contacts::Family::PiecewiseContact;}
}
const char* physicalPolicyClosureSha256() { (void)physicalPolicies();return physical_policy_data::closureSha; }
Policy physicalPolicy(const manual_contacts::SourceHandle& source) {
    need(source.family()==manual_contacts::Family::PhysicalContact,"PHYSICAL_TASK_FAMILY_REQUIRED");
    const auto tag=source.policyTag();
    need(std::holds_alternative<manual_contacts::PhysicalPolicyTag>(tag)&&std::get<manual_contacts::PhysicalPolicyTag>(tag).level==source.level(),"PHYSICAL_TASK_POLICY_TAG_JOIN");
    const auto& d=physical_contacts::definition(source.sourceKey());
    need(physicalPolicies().items.count(d.level()),"PHYSICAL_TASK_POLICY_LEVEL");
    auto p=physicalPolicies().items.at(d.level());
    const auto meta=json::parse(source.trustedMetadataJson());
    need(at(meta,"policy_context_sha256").string()==p.contextSha256,"PHYSICAL_TASK_CONTEXT_JOIN");
    if(p.passes.front().rhythms.empty()) {
        Rhythm r=Rhythm::StraightEighth;
        if(d.level()==16||d.level()==17||d.level()==25||d.level()==26)r=Rhythm::StraightSixteenth;
        else if(d.level()==23||d.level()==24)r=Rhythm::Triplet;
        else if(d.level()==20||d.level()==29) {
            need(d.contactCount()==30||d.contactCount()==78||d.contactCount()==96||d.contactCount()==52||d.contactCount()==66,"PHYSICAL_TASK_CIRCUIT_MODULE_EXTENT");
            r=(d.contactCount()==78||d.contactCount()==66)?Rhythm::Triplet:d.contactCount()==96?Rhythm::StraightSixteenth:Rhythm::StraightEighth;
            p.passes.front().rhythms.push_back(Rhythm::OneNotePerClick);
        } else if(d.level()==32) {need(d.contactCount()==54||d.contactCount()==70,"PHYSICAL_TASK_PENT_ODD_MODULE_EXTENT");r=d.contactCount()==54?Rhythm::Triplet:Rhythm::Quintuplet;}
        else if(d.level()==33) {need(d.contactCount()==36||d.contactCount()==48,"PHYSICAL_TASK_PENT_SKIP_MODULE_EXTENT");r=d.contactCount()==36?Rhythm::StraightEighth:Rhythm::Triplet;}
        p.passes.front().rhythms.push_back(r);
    }
    return p;
}
Policy harmonicPolicy(const manual_contacts::SourceHandle& source) {
    need(source.family()==manual_contacts::Family::HarmonicContact,"HARMONIC_TASK_SOURCE_FAMILY");
    const auto context=json::parse(source.harmonicContextJson());const auto program=json::parse(source.harmonicProgramJson());const auto& ref=at(context,"context_ref");const auto& txt=at(at(at(context,"source_context"),"originals"),"txt");Policy p{};p.level=source.level();p.family=manual_contacts::Family::HarmonicContact;p.sourceTempoRule=false;
    p.contextPath=at(ref,"path").string();p.contextSha256=at(ref,"sha256").string();p.sourceTextPath=at(txt,"path").string();p.sourceTextSha256=at(txt,"sha256").string();
    p.passes.push_back({Pass::SourcePerformance,{source.harmonicMetricEnd()?Rhythm::SourceMetric:Rhythm::Unspecified},{},false});
    const auto& fullContext=at(context,"source_context");
    if(p.level==40)p.sourceInstructionBlocks.push_back(at(at(fullContext,"complete_source_instructions"),"intro_text").string());
    else if(p.level==46)p.sourceInstructionBlocks.push_back(at(at(fullContext,"complete_instructions"),"purpose").string());
    else {
        const auto overview=at(at(fullContext,"source_guidance"),"overview_text").string();
        p.sourceInstructionBlocks.push_back(overview.substr(0,overview.find("MODULE COUNTS")));
    }
    for(const auto& text:at(program,"instruction_blocks").array())p.sourceInstructionBlocks.push_back(text.string());
    p.sourceInstructionBlocks.push_back("The following original progression/mastery instructions are broader manual source duties. This row's reports cannot establish them, parent/book completion or observed mastery.");
    for(const auto& text:at(program,"broader_manual_source_instructions").array())p.sourceInstructionBlocks.push_back(text.string());return p;
}
Policy sourceContactPolicy(const manual_contacts::SourceHandle& source) {
    need(source.family()==manual_contacts::Family::SourceContact,"SOURCE_CONTACT_TASK_SOURCE_FAMILY");
    const auto meta=json::parse(source.trustedMetadataJson()),program=json::parse(source.phaseProgramJson());Policy p{};p.level=source.level();p.family=manual_contacts::Family::SourceContact;p.sourceTempoRule=false;
    const auto& ref=at(meta,"context_ref");p.contextPath=at(ref,"path").string();p.contextSha256=at(ref,"sha256").string();
    p.passes.push_back({Pass::SourcePerformance,{source.phaseMetricEnd()?Rhythm::SourceMetric:Rhythm::Unspecified},{},false});
    for(const auto& text:at(program,"instruction_blocks").array())p.sourceInstructionBlocks.push_back(text.string());
    p.sourceInstructionBlocks.push_back("Follow the exact source unit. Printed references and nonaudible tokens are not new attacks; unknown pitches, fingers, pick starts, clocks and sounding durations are not supplied.");
    return p;
}
Policy piecewisePolicy(const manual_contacts::SourceHandle& source) {
    need(source.family()==manual_contacts::Family::PiecewiseContact,"PIECEWISE_TASK_FAMILY");
    const auto tag=source.policyTag();need(std::holds_alternative<manual_contacts::PiecewisePolicyTag>(tag)&&std::get<manual_contacts::PiecewisePolicyTag>(tag).level==source.level(),"PIECEWISE_TASK_TAG");
    const auto& d=piecewise_contacts::definition(source.sourceKey());const auto obj=json::parse(d.trustedContextJson());const auto& ctx=at(obj,"source_context");const auto meta=json::parse(d.trustedMetadataJson());Policy p{};
    p.level=d.level();p.family=manual_contacts::Family::PiecewiseContact;const auto& r=at(obj,"context_ref");const auto& txt=at(at(ctx,"originals"),"txt");
    p.contextPath=at(r,"path").string();p.contextSha256=at(r,"sha256").string();p.sourceTextPath=at(txt,"path").string();p.sourceTextSha256=at(txt,"sha256").string();
    need(at(meta,"context_sha256")==J(p.contextSha256),"PIECEWISE_TASK_SOURCE_CONTEXT");
    for(const auto& line:at(ctx,"guidance_lines").array()){const auto n=integer(at(line,"line"));p.sourceLines.push_back({n,at(line,"text").string()});p.safeInstructionLines.push_back(n);}
    const auto& guidance=at(ctx,"semantic_guidance");
    if(p.level==34)for(const auto* key:{"counts_picking_text","seam_instruction_text","practice_mastery_text"})p.sourceInstructionBlocks.push_back(at(guidance,key).string());
    else {need(p.level==35,"PIECEWISE_TASK_LEVEL");for(const auto* key:{"picking","module_a","txt"})p.sourceInstructionBlocks.push_back(at(guidance,key).string());}
    const auto family=at(at(meta,"route_projection"),"family").string();
    const auto rhythm=p.level==35?Rhythm::OneNotePerClick:family=="vertical"?Rhythm::StraightEighth:Rhythm::StraightSixteenth;
    p.passes.push_back({Pass::SourcePerformance,{rhythm},p.safeInstructionLines,false});
    p.sourceTempoRule=true;p.advancementNeedsTwoDays=true;p.advancementNeedsBothStarts=true;p.advancementNeedsBothRoutes=true;
    auto duty=[&](SourceDuty id,const std::string& label,bool release=false){p.sourceDuties.push_back({id,label,p.safeInstructionLines,release});};
    duty(SourceDuty::SourceMapNaming,p.level==34?"Name all five positions, spans, starting degrees and A roots from the original source":"Name all six original lane notes, degrees and A roots");
    duty(SourceDuty::UnselectedSourceBranches,p.level==34?"Other source choices: descending-first position study and complete-workout sixteenths are separate manual source traversals; the displayed default contacts are not their realization":"Complete the other printed seam-slide, finger-1 destination and linked-snake modules from the original source; no slide/legato/alternate contacts generated here");
    duty(SourceDuty::FullRoute,p.level==34?"Play forward60 plus reverse60 as the original linked120 circuit, re-picking high-e17 at the turn with uninterrupted D/U; complete the other position/seam cells separately":"Complete all six silent12-note lanes and the original forward36/reverse36 linked72 snake with continuous D/U; other printed modules remain separate",true);
    duty(SourceDuty::RootAccentThenRemove,p.level==34?"After the complete linked source circuit, accent every A root and then remove those accents while hearing A as tonic":"After the complete linked72-note source circuit, accent A roots and then remove the accents");
    duty(SourceDuty::ThreeCleanRoundTrips,p.level==34?"Report three clean complete circuits at the actual current source route length before a next-session +2 BPM plan":"Report three clean complete runs at the actual current source route length before a next-session +2 BPM plan");
    duty(SourceDuty::ShortenedRouteRepair,p.level==34?"Stop, shake out after tension, and practice one adjacent-position seam instead of forcing the full route; after two errors this is the printed alternative to reducing4–6 BPM":"Stop the full route after tension and return to one string; after two errors shorten to one lane/seam as the printed alternative to reducing4–6 BPM",true);
    duty(SourceDuty::NoisePressureThumbRepair,"Release pressure earlier, move the thumb with the hand, and then apply the printed4–6 BPM reduction",true);
    duty(SourceDuty::ExactCountAirPickingRepair,p.level==34?"Mute strings and air-pick the actual printed12-,30-,or60-note count without a pick reset":"Mute strings and air-pick the actual printed12-,36-,or72-note count without a pick reset",true);
    if(p.level==34){duty(SourceDuty::LostKeyRootRepair,"Stop on the nearest original A root, sing A, and restart the local frame",true);duty(SourceDuty::WrongPositionNamingRepair,"Name the original position span and its first low-E degree before playing");duty(SourceDuty::EarlyShiftAnchorRepair,"Remain in the lower frame through the shared anchor; move only after it sounds",true);}
    else duty(SourceDuty::WrongPositionNamingRepair,"Name and look at the original destination before leaving the launch note");
    return p;
}
Task::Task(const Definition& definition) : Task(manual_contacts::SourceHandle::ordered(definition)) {}
Task::Task(const manual_contacts::SourceHandle& source)
    : source_(source), legacyDefinition_(source.family()==manual_contacts::Family::OrderedContact
        ?std::optional<Definition>(ordered_contacts::definition(source.sourceKey())):std::nullopt),
      policy_(source.family()==manual_contacts::Family::OrderedContact?policy(source.level()):source.family()==manual_contacts::Family::PhysicalContact?physicalPolicy(source):source.family()==manual_contacts::Family::HarmonicContact?harmonicPolicy(source):source.family()==manual_contacts::Family::SourceContact?sourceContactPolicy(source):piecewisePolicy(source)),owner_(nextOwner.fetch_add(1)) {
    need(owner_ != 0 && owner_ != std::numeric_limits<std::uint64_t>::max(), "ORDERED_TASK_OWNER_EXHAUSTED");
    const auto meta=json::parse(source_.trustedMetadataJson());
    for (const auto& heading:at(harmonic(policy_)?at(meta,"unit"):meta,"heading_path").array())headings_.push_back(heading.string());
    if(harmonic(policy_)){harmonicProgram_=json::parse(source_.phaseProgramJson());harmonicSourceAtoms_=json::parse(source_.phaseAtomsJson());
        if(sourceContact(policy_)){harmonicSourceContracts_=J::Object{};sourceCompletedRoutes_.assign(source_.sourceRouteCount(),false);for(const auto& r:at(meta,"routes").array())routes_.push_back(at(r,"label").string());}
        else {harmonicSourceContracts_=at(meta,"source_contracts");routes_={"Exact original written contact order"};}need(!headings_.empty(),"HARMONIC_TASK_HEADING");}
    else if(piecewise(policy_)) {
        const auto& parts=at(at(meta,"route_projection"),"parts").array();for(const auto& part:parts)routes_.push_back(at(part,"label").string());
        need(!headings_.empty()&&!routes_.empty(),"PIECEWISE_TASK_ROUTE_PARTS");
    } else if(physical(policy_)) {
        routes_={"Printed ascending half of this cell/module","Printed descending half of this cell/module"};
        need(!headings_.empty()&&source_.contactCount()%2==0,"PHYSICAL_TASK_CELL_ROUTES");
    } else {
        for (const auto& step:at(meta,"unit_direction_task_steps").array()) {
            const auto& text=at(step,"text").string();
            if(text.rfind("ASCEND",0)==0||text.rfind("DESCEND",0)==0||text.rfind("SHIFT ",0)==0)routes_.push_back(text);
        }
        need(!headings_.empty()&&routes_.size()==2&&source_.contactCount()%2==0,"ORDERED_TASK_SOURCE_UNIT_ROUTES");
        const auto& assets=at(at(meta,"source_context"),"source_assets").array();
        need(std::any_of(assets.begin(),assets.end(),[this](const auto& r){return at(r,"path").string()==policy_.sourceTextPath&&at(r,"sha256").string()==policy_.sourceTextSha256;}),"ORDERED_TASK_POLICY_SOURCE_JOIN");
    }
}
const Definition& Task::definition() const {need(legacyDefinition_.has_value(),"PHYSICAL_TASK_HAS_NO_ORDERED_DEFINITION");return *legacyDefinition_;}
std::string Task::fullSourceGuidanceJson() const {
    auto guidance=harmonic(policy_)?json::parse(source_.phaseContextJson()):piecewise(policy_)?json::parse(piecewise_contacts::definition(sourceKey()).trustedContextJson()):physical(policy_)?physicalPolicies().encoded.at(policy_.level):policies().encoded.at(policy_.level);
    guidance.object().emplace("exact_unit",json::parse(source_.trustedMetadataJson()));
    guidance.object().emplace("manual_only",true);guidance.object().emplace("acoustic_sounding_span",nullptr);
    return json::stringify(guidance);
}
std::vector<ActionDescriptor> Task::actionDescriptors() const {
    if(sourceContact(policy_))return sourceContactActionDescriptors();
    if(harmonic(policy_))return harmonicActionDescriptors();
    std::vector<ActionDescriptor> out;
    const auto sourceLines = [this](const std::vector<int>& selected) {
        std::vector<std::string> text;
        for (const auto& line : policy_.sourceLines) if (includes(selected, line.line)) text.push_back(line.text);
        return text;
    };
    const auto rhythms = [](const std::vector<Rhythm>& values) {
        std::vector<ChoiceDescriptor> choices;
        for (const auto r : values) choices.push_back({r, label(r)});
        return choices;
    };
    const auto observations = [this] {
        std::vector<ChoiceDescriptor> choices{{Observation::Unknown, "Not sure"}, {Observation::Clean, "Clean loop"},
            {Observation::Error, "Error"}, {Observation::RisingTension, "Rising tension"}};
        if (!physical(policy_) && policy_.level >= 5 && policy_.level <= 7) choices.push_back({Observation::NoisyGap, "Noisy skipped string or gap"});
        if (!physical(policy_) && policy_.level >= 8) choices.push_back({Observation::LateLanding, "Late or missed landing"});
        if (!physical(policy_) && policy_.level >= 9) choices.push_back({Observation::Slide, "Unwanted slide"});
        if (!physical(policy_) && (policy_.level == 8 || policy_.level >= 10)) choices.push_back({Observation::Squeak, "Fret squeak"});
        if(piecewise(policy_)) {
            choices.push_back({Observation::DraggedShiftNoise,"Noisy source shift"});
            choices.push_back({Observation::WrongPosition,"Wrong position or searching for the destination"});
            choices.push_back({Observation::PickReset,"Pick cycle restarted"});
            if(policy_.level==34){choices.push_back({Observation::LostKeyCenter,"Lost A key center"});choices.push_back({Observation::EarlyShift,"Moved before the shared anchor sounded"});}
        } else if(physical(policy_)&&policy_.sourceTempoRule) {
            choices.push_back({Observation::UnevenPulse,"Uneven source group pulse"});
            choices.push_back({Observation::DraggedShiftNoise,"Dragged shift noise"});
            if(policy_.level==16||policy_.level==17||policy_.level==25||policy_.level==26)choices.push_back({Observation::CrossingAccent,"Unwanted crossing accent"});
            if(policy_.sourceGeometryObservation)choices.push_back({Observation::GeometryError,"Assigned frame geometry error"});
        }
        return choices;
    };
    for (const auto action : {Action::Begin, Action::Contact, Action::BoundaryReport, Action::Release,
        Action::LoopReport, Action::OppositeStart, Action::Repeat, Action::AdvancePass, Action::Finish,
        Action::Retry, Action::Cancel, Action::Restart, Action::SessionReport, Action::ReduceTempo,
        Action::PlanIncrease, Action::ExtensionReport, Action::SourcePracticeReport, Action::SourceIssueReport}) {
        try { requireAllowed(action); } catch (const Refusal&) { continue; }
        ActionDescriptor d{action, {}, {}, {}, {}};
        switch (action) {
        case Action::Begin: {
            d.label = "Begin the source-guided exercise";
            for(const auto& block:policy_.sourceInstructionBlocks)d.instructions.push_back(block);
            for (const auto& line : policy_.sourceLines) {
                if(physical(policy_)&&!includes(policy_.safeInstructionLines,line.line))continue;
                if (line.text.rfind("SET ", 0) == 0) break;
                if (!line.text.empty() && line.text.find_first_not_of("=- ") != std::string::npos) d.instructions.push_back(line.text);
            }
            d.instructions.push_back((physical(policy_)?"Follow this exact printed cell or module: ":"Follow this printed set and mode: ") + headings_.front()
                + (policy_.oneModePerSession ? "; " + headings_.back() : ""));
            std::vector<ChoiceDescriptor> branches{{Branch::PrintedPassProgression, "Printed pass progression"}};
            auto availableRhythms = policy_.passes.front().rhythms;
            if (policy_.restoreAfterStable || policy_.restoreAfterAdvancement) {
                branches.push_back({Branch::RestoredPulse, "Restore triplet or quintuplet after the source prerequisites"});
                if (!includes(availableRhythms, Rhythm::Triplet)) availableRhythms.push_back(Rhythm::Triplet);
                if (!includes(availableRhythms, Rhythm::Quintuplet)) availableRhythms.push_back(Rhythm::Quintuplet);
                d.instructions.push_back("Use the restored-pulse branch for triplet or quintuplet, after the printed straight passes and prerequisites.");
            }
            if(policy_.groupedBeforeDisplacement) {
                branches.push_back({Branch::DisplacementVariation,"Optional sixteenth displacement after the grouped pulse is secure"});
                if(!includes(availableRhythms,Rhythm::StraightSixteenth))availableRhythms.push_back(Rhythm::StraightSixteenth);
            }
            d.fields.push_back(choiceField(FieldId::Branch, "Practice branch", std::move(branches)));
            d.fields.push_back(choiceField(FieldId::Rhythm, "Rhythm or untimed pass", rhythms(availableRhythms)));
            std::vector<ChoiceDescriptor> starts{{Start::Down, "Downstroke start"}};
            if (!policy_.downStartFirst) starts.push_back({Start::Up, "Upstroke start"});
            d.fields.push_back(choiceField(FieldId::FirstStart, "First pick start", std::move(starts)));
            d.fields.push_back(reportField(FieldId::SetupRead, "I read the movement, picking and practice instructions"));
            d.fields.push_back(reportField(FieldId::OneSet, physical(policy_)?"I chose this exact printed cell or module for this study":"I chose this single printed 12-exercise set for this session"));
            if (policy_.oneModePerSession) d.fields.push_back(reportField(FieldId::PrintedMode, "I chose this printed mode for this session"));
            d.fields.push_back(reportField(FieldId::StableLandings, "The required crossings or landings are stable", false));
            d.fields.push_back(bpmField(FieldId::ChosenBpm, "My chosen BPM, if known"));
            if (policy_.previousLevel) {
                d.fields.push_back(bpmField(FieldId::PreviousCleanBpm, "My clean Level " + std::to_string(policy_.previousLevel) + " tempo, if known"));
                if (policy_.slowerOfTwoPreviousModes) d.fields.push_back(bpmField(FieldId::OtherModeCleanBpm, "My other previous-level mode's clean tempo, if known"));
            }
            break;
        }
        case Action::Contact: {
            const auto c = cue();
            const std::string strings[] = {"low E", "A", "D", "G", "B", "high e"};
            d.label = "I played this contact";
            d.instructions = physical(policy_)?std::vector<std::string>{"Use the chosen printed rhythm manually; retain the exact assigned fingers, contact order and continuous alternate picking.",
                "This display realizes this cell or module only. Broader source routes and links have separate manual reports."}:sourceLines(policy_.passes[passIndex_].sourceLines);
            const auto timing = c.clockAuthority == ClockAuthority::SavedSelectedRelativeSlots
                ? "Follow the selected written hand-slot order manually. Sounding duration is unspecified."
                : "Follow this source pass manually. No beat-to-quarter clock is assigned to this pass.";
            d.contact = ContactDescriptor{c.ordinal, strings[c.stringLowToHigh - 1], c.pick, c.route, c.fret, c.finger, c.landingAccent, timing};
            d.fields.push_back(reportField(FieldId::ContactReported, "I manually played the displayed contact"));
            break;
        }
        case Action::BoundaryReport: {
            const auto c = cue(); d.label = "Report the source boundary";
            if (c.releaseAndRelocateBefore) {
                d.instructions.push_back(piecewise(policy_)?"Release pressure and relocate the assigned frame silently before the printed next station. Preserve the pick cycle; this report is not an added musical rest.":physical(policy_)?"Release pressure and rebuild the assigned hand frame for the printed G-string backreach or B-string geometry; retain the assigned finger and pick continuity.":"Release pressure and relocate the whole hand frame to the next printed position; use its assigned finger.");
                d.fields.push_back(reportField(FieldId::PressureReleased, "I released fretting pressure"));
                d.fields.push_back(reportField(FieldId::FrameRelocated, physical(policy_)?"I rebuilt the complete assigned hand frame":"I relocated the whole hand frame"));
            }
            if(c.rebuildAssignedFingeringBefore&&!c.releaseAndRelocateBefore) {
                d.instructions.push_back(piecewise(policy_)?"Move only after the printed shared anchor/position endpoint and use the complete assigned next frame. Preserve picking; this report adds no rest or anchor attack.":"Rebuild the assigned fingering for the source G-to-B tuning offset; preserve the printed finger and alternate pick.");
                d.fields.push_back(reportField(FieldId::FrameRelocated,"I rebuilt the assigned fingering"));
            }
            if (c.pauseBefore != Pause::None) {
                d.instructions.push_back(c.pauseBefore == Pause::OneSubdivisionAtShift ? "Pause one subdivision at this shift."
                    : c.pauseBefore == Pause::StopAndRelocate ? "Stop, release and relocate before continuing. Do not slide along the string."
                    : "Separate this four-note cell from the next.");
                d.fields.push_back(reportField(FieldId::PauseReported, "I followed the source pause, stop or separation"));
            }
            d.instructions.push_back("Continue alternate picking without restarting the pick cycle.");
            break;
        }
        case Action::Release:
            d.label = "Report complete hand release";
            d.instructions = {"Release the hands before reviewing this traversal or closing the cancellation."};
            d.fields.push_back(reportField(FieldId::HandReleaseReported, "I completely released the hands")); break;
        case Action::LoopReport:
            d.label = "Report this loop";
            d.instructions = {"These are your reports. A displayed or acknowledged cue does not establish clean performance."};
            d.fields.push_back(choiceField(FieldId::Observation, "What happened?", observations()));
            d.fields.push_back(reportField(FieldId::StableLandings, "The required landings are stable", false)); break;
        case Action::OppositeStart: d.label = "Repeat the full route with the opposite pick start"; break;
        case Action::Repeat: d.label = "Repeat both pick starts"; break;
        case Action::Retry: d.label = "Retry this pass and pick start"; break;
        case Action::AdvancePass: {
            const auto& next = policy_.passes[passIndex_ + 1]; d.label = "Continue to the next printed pass";
            d.instructions = sourceLines(next.sourceLines);
            d.fields.push_back(choiceField(FieldId::NextPass, "Required next pass", {{next.pass, label(next.pass)}}));
            auto nextRhythms = policy_.level >= 8 ? next.rhythms : std::vector<Rhythm>{rhythm_};
            if (policy_.restoreAfterAdvancement)
                nextRhythms.erase(std::remove_if(nextRhythms.begin(), nextRhythms.end(), specialPulse), nextRhythms.end());
            d.fields.push_back(choiceField(FieldId::Rhythm, "Rhythm", rhythms(nextRhythms)));
            break;
        }
        case Action::SourceIssueReport:
            {auto issues=observations();issues.erase(std::remove_if(issues.begin(),issues.end(),[](const auto& c){return std::get<Observation>(c.value)==Observation::Clean;}),issues.end());
            d.label="Stop and report a source issue";d.instructions={"Report the actual source issue at this contact. Stop and explicitly release before the printed repair. The owner retains your source key, cursor, debt and history; no performance is inferred."};d.fields.push_back(choiceField(FieldId::Observation,"Source issue",std::move(issues)));break;}
        case Action::Finish:
            d.label = "Close this reported traversal branch";
            d.instructions = {physical(policy_)?"This closes the reported cell/module and chosen pulse only. Broader neck routes, module links, partial studies, ear/comparison duties and separate-day conditions remain separately reported source obligations.":"The other exercises in the set, other required sessions and separate-day conditions remain your broader practice obligations."}; break;
        case Action::Cancel: d.label = "Cancel and release"; break;
        case Action::Restart: d.label = "Set up this same printed exercise again"; break;
        case Action::SessionReport:
            d.label = "Report broader source practice conditions";
            d.instructions = {"Report the printed set and session conditions separately. This exercise does not observe or certify them."};
            d.fields.push_back(reportField(FieldId::PriorPrintedPasses, "I previously completed the required printed passes", false));
            d.fields.push_back(reportField(FieldId::FullSetClean, physical(policy_)?"The full source route is clean, as my manual report":"The full printed set is clean", false));
            if (policy_.advancementNeedsBothRoutes) d.fields.push_back(reportField(FieldId::BothRoutesClean, "The set is clean in both directions", false));
            if (policy_.advancementNeedsBothStarts) d.fields.push_back(reportField(FieldId::BothStartsClean, "The set is clean with both pick starts", false));
            if (policy_.advancementNeedsBothModes) d.fields.push_back(reportField(FieldId::BothModesClean, "Both source modes are clean", false));
            if (policy_.advancementNeedsTwoDays) d.fields.push_back({FieldId::SeparateDays, FieldKind::DateList,
                "Separate practice days I report (YYYY-MM-DD)", false, {}, {}, {}, {}});
            if (policy_.rotationAcrossSessions || policy_.restoreAfterStable || policy_.restoreAfterAdvancement)
                d.fields.push_back(choiceField(FieldId::NextSessionRhythm, "Next session's source grouping", rhythms({Rhythm::StraightSixteenth, Rhythm::Triplet, Rhythm::Quintuplet}), false));
            break;
        case Action::ReduceTempo:
            d.label = "Report the source tempo reduction";
            d.instructions = {piecewise(policy_)?"Apply the printed 4–6 BPM reduction after a noisy shift, or choose it after two errors. The printed stop and shorter-route repair remains separate; a new setup does not erase either obligation.":"After two source errors or rising tension, reduce 4–6 BPM. A new setup does not erase this pending reduction."};
            d.fields.push_back(choiceField(FieldId::TempoDrop, "Reduce by", {{4, "4 BPM"}, {5, "5 BPM"}, {6, "6 BPM"}}));
            d.fields.push_back(reportField(FieldId::AppliedReduction, "I applied this reduction")); break;
        case Action::PlanIncrease:
            d.label = "Plan +2 BPM for the next session";
            d.instructions = {piecewise(policy_)?"After three separately reported clean complete circuits/runs at the current original route length, plan +2 BPM for the next session. No current tempo or clock is inferred.":physical(policy_)?"After three separately reported clean complete source round trips, plan +2 BPM for the next session. Individual cell/module loops do not establish this prerequisite.":"After three reported clean loops, add 2 BPM next time. The current tempo stays unchanged."};
            d.fields.push_back(reportField(FieldId::PlannedIncrease, "I plan this increase next session")); break;
        case Action::SourcePracticeReport: {
            d.label="Report separate source practice";
            d.instructions={"Choose a printed source duty and report your own manual practice. This report does not supply missing route/module contacts, known pitches, a clock, or an observed result.",
                "For route/link duties, report pressure release and complete frame relocation. Also report the source pause for neighboring-rung or paused-circuit practice. Optional fields become required when the selected duty needs them."};
            std::vector<ChoiceDescriptor> choices;
            for(const auto& duty:policy_.sourceDuties) {
                choices.push_back({duty.duty,duty.label});
                for(const auto& line:sourceLines(duty.sourceLines))d.instructions.push_back(line);
            }
            d.fields.push_back(choiceField(FieldId::SourceDutyChoice,"Printed source duty",std::move(choices)));
            d.fields.push_back(reportField(FieldId::SourcePracticeReported,"I manually practiced the selected source duty"));
            d.fields.push_back(reportField(FieldId::SourceReleaseReported,"I released fretting pressure at the required source boundaries",false));
            if(!piecewise(policy_))d.fields.push_back(reportField(FieldId::FrameRelocated,"I relocated the complete hand-and-thumb frame at the required source boundaries",false));
            d.fields.push_back(reportField(FieldId::PauseReported,piecewise(policy_)?"I stopped and followed the printed shorter-route repair":"I used the source end-cell or module pauses",false));break;
        }
        case Action::SourcePhaseReport: case Action::SourceRepairReport: break;
        case Action::ExtensionReport: {
            d.label = "Plan an optional source extension";
            d.instructions = {"Follow these separate source instructions manually. The base contact display does not realize changed distances or alternating modes."};
            std::vector<ChoiceDescriptor> choices;
            for (const auto e : policy_.extensions) {
                const auto g = extensionGuidance(e);
                for (const auto& line : g.sourceLines) if (!line.text.empty()) d.instructions.push_back(line.text);
                choices.push_back({e, e == Extension::AlternatingModes ? "Alternate 3+1 and 1+3 between successive skip pairs"
                    : e == Extension::DistanceP5P8P11 ? "P5 > P8 > P11 and descending equivalent"
                    : e == Extension::DistanceP5P7P10 ? "P5 > P7 > P10 and descending equivalent"
                    : "Other position distances, preserving 1+2+1 and the descending equivalent"});
            }
            d.fields.push_back(choiceField(FieldId::ExtensionChoice, "Source extension", std::move(choices)));
            d.fields.push_back(reportField(FieldId::MasteryReported, "I report the source's mastery prerequisites as met"));
            if (includes(policy_.extensions, Extension::OtherPositionDistance)) {
                for (const auto pair : {std::pair<FieldId, const char*>{FieldId::PositionOne, "First position frame"},
                    {FieldId::PositionTwo, "Middle position frame"}, {FieldId::PositionThree, "Last position frame"}}) {
                    auto field = bpmField(pair.first, pair.second); field.required = true;
                    field.onlyForExtension = Extension::OtherPositionDistance; d.fields.push_back(std::move(field));
                }
            }
            break;
        }
        }
        out.push_back(std::move(d));
    }
    return out;
}
bool Task::advancementReported() const {
    if (!sessionReport_ || !policy_.advancementNeedsTwoDays) return false;
    const auto& report = *sessionReport_;
    return report.fullPrintedSetClean == Claim::Yes && report.separateDayLabels.size() >= 2
        && (!policy_.advancementNeedsBothModes || report.bothModesClean == Claim::Yes)
        && (!policy_.advancementNeedsBothStarts || report.bothStartsClean == Claim::Yes)
        && (!policy_.advancementNeedsBothRoutes || report.bothRoutesClean == Claim::Yes);
}
harmonic_contacts::Cue Task::harmonicCue()const{
    need(harmonic(policy_)&&!sourceContact(policy_)&&setupDone_&&state_==State::Traversal,"HARMONIC_TASK_NO_ACTIVE_SOURCE_CUE");
    return source_.harmonicContact(nextOrdinal_,neutral(start_));
}
source_contacts::Cue Task::sourceAtomCue()const{
    need(sourceContact(policy_)&&setupDone_&&state_==State::Traversal,"SOURCE_CONTACT_TASK_NO_ACTIVE_CUE");
    if(!sourceOwnedContacts_.empty()){auto c=sourceOwnedContacts_.at(nextOrdinal_-1);c.routeIndex=passIndex_;for(auto& a:c.atoms)a.pick=((nextOrdinal_-1)%2==0)==(start_==Start::Down)?"D":"U";return c;}
    return source_.sourceAtomContact(nextOrdinal_,neutral(start_),passIndex_);
}
std::size_t Task::activeSourceContactCount()const{return sourceContact(policy_)?(!sourceOwnedContacts_.empty()?sourceOwnedContacts_.size():source_.sourceRouteContactCount(passIndex_)):source_.contactCount();}
bool Task::allRequiredSourceRoutesReported()const{
    if(!sourceContact(policy_))return true;const auto meta=json::parse(source_.trustedMetadataJson());const auto& routes=at(meta,"routes").array();
    for(std::size_t n=0;n<routes.size();++n)if(at(routes[n],"source_required").boolean()&&!sourceCompletedRoutes_[n])return false;return true;
}
State Task::sourceStateAfterPhase()const{
    const auto& phases=at(harmonicProgram_,"report_phases").array();
    if(harmonicPhaseIndex_<phases.size()&&static_cast<std::size_t>(integer(at(phases[harmonicPhaseIndex_],"after_source_ordinal")))==nextOrdinal_-1)return State::SourcePhase;
    return nextOrdinal_>activeSourceContactCount()?State::Review:State::Traversal;
}
std::vector<ActionDescriptor> Task::sourceContactActionDescriptors()const{return harmonicActionDescriptors();}
std::vector<ActionDescriptor> Task::harmonicActionDescriptors()const{
    std::vector<ActionDescriptor> out;
    for(const auto action:{Action::Begin,Action::Contact,Action::Release,Action::SourcePhaseReport,
        Action::SourceRepairReport,Action::SourceIssueReport,Action::OppositeStart,Action::Repeat,
        Action::Retry,Action::Finish,Action::Cancel,Action::Restart,Action::AdvancePass}){
        try{requireAllowed(action);}catch(const Refusal&){continue;}
        ActionDescriptor d{action,{},{},{},{}};
        switch(action){
        case Action::Begin:{
            d.label="Begin this exact written source unit";d.instructions=policy_.sourceInstructionBlocks;
            d.instructions.push_back("Source-null fingering, rhythm and pick starts remain unspecified. There is no clock, sounding gate, generated alternative or observed performance.");
            d.fields={choiceField(FieldId::Branch,"Written source traversal",{{Branch::PrintedPassProgression,"Exact original written order"}}),
                choiceField(FieldId::Rhythm,"Source timing",{{policy_.passes[0].rhythms[0],source_.phaseMetricEnd()?(sourceContact(policy_)?"Original source-relative hand slots; no clock":"Original printed quarter hand slots; no clock"):"Numeric source rhythm unspecified; follow written order manually"}}),
                reportField(FieldId::SetupRead,"I read this source unit's instructions"),reportField(FieldId::OneSet,"I chose this exact printed unit")};
            d.fields.push_back(at(harmonicProgram_,"requires_both_saved_starts").boolean()?choiceField(FieldId::FirstStart,"First original pick start",{{Start::Down,"Downstroke"},{Start::Up,"Upstroke"}}):choiceField(FieldId::FirstStart,"Source pick start",{{Start::Unspecified,"Source does not prescribe a saved pick start"}}));break;}
        case Action::Contact:{
            if(sourceContact(policy_)){
                const auto c=sourceAtomCue();d.label=c.simultaneous?"Report this atomic source group":"Acknowledge this exact source atom";
                d.instructions={c.simultaneous?"Play this printed simultaneous group together; its members are not serial attacks.":"Follow this source atom's printed physical/technique duty. A reference or muted token is not a new pitched attack.","Reports are manual declarations; sounding duration and clock remain unknown."};
                if(c.ordinal==1)for(const auto& text:at(harmonicProgram_,"instruction_blocks").array())d.instructions.push_back(text.string());
                for(const auto& a:c.atoms){
                    std::string line="Source atom "+std::to_string(a.sourceOrdinal)+": "+a.stringLabel;
                    if(a.physicalFret)line+=" physical fret "+std::to_string(*a.physicalFret);else line+=" physical fret unspecified";
                    if(a.soundingFret&&a.soundingFret!=a.physicalFret)line+="; sounding target fret "+std::to_string(*a.soundingFret);
                    if(a.referenceFret)line+="; printed reference/ceiling fret "+std::to_string(*a.referenceFret);
                    if(!a.spelling.empty())line+="; written note "+a.spelling;
                    line+="; "+a.kind;if(!a.attack.empty())line+="; "+a.attack;if(!a.technique.empty())line+="; printed technique "+a.technique;
                    if(a.finger)line+=(a.kind=="learner_owned_source_domain_contact"?"; learner-chosen finger ":"; printed finger ")+std::to_string(*a.finger);else line+="; finger unspecified";
                    if(a.pick)line+="; "+*a.pick;else line+=a.picked==false?"; no new pick":"; pick direction unspecified";
                    if(a.audible==false)line+="; NONAUDIBLE reference/preparation";d.instructions.push_back(line+".");
                    const auto facts=json::parse(a.sourceFactsJson),annotations=json::parse(a.annotationsJson);
                    for(const auto* field:{"harmony","harmonic_role","degree","printed_degree","source_hold_beats","mute_at_source_beat","source_bar","duration_source_bars","sustain_from_previous_bar","color"}){
                        if(const auto* v=facts.find(field);v&&!v->null()){need(v->isString()||v->isBool()||v->isNumber(),"SOURCE_CONTACT_LEARNER_FACT_TYPE");d.instructions.push_back(std::string(field)+": "+(v->isString()?v->string():json::stringify(*v))+".");}
                    }
                    if(const auto* position=facts.find("relative_position")){need(position->isObject(),"SOURCE_SYMBOLIC_POSITION_OBJECT");for(const auto* k:{"bar","beat","phase"}){const auto& v=at(*position,k);d.instructions.push_back(std::string("Original source ")+k+": "+(v.isString()?v.string():json::stringify(v))+"; symbolic, unclocked.");}}
                    if(const auto* role=facts.find("harmonic_role");role&&*role==J("R"))d.instructions.push_back("R is the printed harmonic root, not a rest; attack and audibility retain their separate source facts.");
                    if(const auto* accent=facts.find("source_accent")){need(accent->isBool(),"SOURCE_CONTACT_QUALITATIVE_ACCENT_TYPE");d.instructions.push_back(accent->boolean()?"Apply the source qualitative root accent here; no numeric velocity is supplied.":"This contact is outside the source root-accent set.");}
                    for(const auto* field:{"Nte","Rol","Job","Deg","F#m","Amaj","Col","Set","spoken_source_degree","OriginalWrittenNote"})if(const auto* v=annotations.find(field);v&&!v->null()){need(v->isString(),"SOURCE_CONTACT_PRINTED_ANNOTATION_TYPE");d.instructions.push_back(std::string("Printed ")+field+": "+v->string()+".");}
                    if(a.onset)d.instructions.push_back("Source-relative authored onset cue "+std::to_string(a.onset->numerator())+"/"+std::to_string(a.onset->denominator())+"; no seconds or inferred beat coupling.");
                    if(a.handSlotDuration)d.instructions.push_back("Authored hand slot "+std::to_string(a.handSlotDuration->numerator())+"/"+std::to_string(a.handSlotDuration->denominator())+"; this is not a sounding gate.");
                }
                if(!c.atoms.empty()) {const auto& a=c.atoms.front();ContactDescriptor cd{c.ordinal,a.stringLabel,a.pick.value_or(""),routes_[passIndex_],a.physicalFret.value_or(0),a.finger,false,"Source-relative manual cue only; acoustic clock/gate unknown."};cd.sourceAtomDescriptor=true;cd.sourcePhysicalFret=a.physicalFret;cd.sourceSoundingFret=a.soundingFret;cd.sourceReferenceFret=a.referenceFret;cd.sourceAtomKind=a.kind;cd.sourceAudible=a.audible;cd.sourcePickAttack=a.picked;cd.sourceMidi=a.midi;d.contact=cd;}
                d.fields={reportField(FieldId::ContactReported,c.simultaneous?"I manually followed this complete atomic group":"I followed this exact source atom; references acknowledged without extra attack")};break;
            }
            const auto c=harmonicCue();d.label="Report this original source contact";d.instructions={"Retain the printed contact, note/color and applicable chord role; source-null fingers and pick starts are not supplied.","A manual acknowledgement is not an observed or acoustic result."};
            const auto& atom=harmonicSourceAtoms_.array()[c.ordinal-1];
            d.instructions.push_back("Written note: "+c.spelling+".");
            const auto fact=[&](const char* field,const char* label){const auto* v=atom.find(field);if(v&&!v->null()){need(v->isString(),"HARMONIC_LEARNER_SOURCE_FACT_TYPE");d.instructions.push_back(std::string(label)+v->string()+".");}};
            fact("harmony","Active source chord: ");fact("harmonic_role","Source chord role: ");
            if(const auto* role=atom.find("harmonic_role");role&&*role==J("R"))d.instructions.push_back("R is the harmonic root, not a rest; this is a picked contact.");
            fact("degree",policy_.level==40?"Printed F#-minor degree: ":"Printed degree: ");fact("position","Source position: ");
            if(const auto* color=atom.find("color");color&&!color->null()){
                const std::map<std::string,std::string> meanings{{"C","common to both sets"},{"M","major-only"},{"m","minor-only"},{"*","chord-completion tone"}};
                need(color->isString()&&meanings.count(color->string()),"HARMONIC_PRINTED_COLOR_WHITELIST");
                d.instructions.push_back("Printed color: "+color->string()+" ("+meanings.at(color->string())+").");
            }
            if(const auto* pool=atom.find("source_pitch_pool");pool&&!pool->null()){
                need(pool->isString()&&(pool->string()=="MIN"||pool->string()=="MAJ"),"HARMONIC_SOURCE_POOL_WHITELIST");
                d.instructions.push_back("Pitch pool: "+pool->string()+(pool->string()=="MIN"?" (A minor pentatonic)":" (A major pentatonic)")+"; this is a pool label, not a backing chord.");
            }
            if(const auto* completion=atom.find("completion_tone");completion&&*completion==J(true))d.instructions.push_back("Printed completion tone: *; use it for its source chord-completion job, then return to the original core pool.");
            if(policy_.level==47&&c.spelling=="G#")d.instructions.push_back("G#* is the printed E7 completion tone, not a pentatonic member; the separate direct-E7 approach repair is not an alternative displayed contact.");
            if(const auto* qa=harmonicSourceContracts_.find("question_answer_contract"))d.instructions.push_back("Written call/answer context: "+at(*qa,"source_heading").string()+"; change color after contact4 and keep the same neck area.");
            for(const auto& phase:at(harmonicProgram_,"report_phases").array())if(!at(phase,"manual_material_separate_from_displayed_contacts").boolean()) {
                const auto& extent=at(phase,"source_extent").array();
                if(static_cast<std::size_t>(integer(extent[0]))<=c.ordinal&&c.ordinal<=static_cast<std::size_t>(integer(extent[1])))
                    for(const auto& text:at(phase,"instructions").array())d.instructions.push_back(text.string());
            }
            d.contact=ContactDescriptor{c.ordinal,c.stringLabel,c.pick.value_or(""),"Original written source order",c.fret,c.finger,false,c.sourceMetricSpan?"Only this model retains its original quarter hand slot; sounding duration and clock are unknown.":"Source ordinal/group only; numeric onset, duration and sounding gate are unspecified."};
            d.fields={reportField(FieldId::ContactReported,"I manually played this source contact")};break;}
        case Action::SourcePhaseReport:{
            const auto& phase=at(harmonicProgram_,"report_phases").array()[harmonicPhaseIndex_];d.label="Report the written source criterion";for(const auto& text:at(phase,"instructions").array())d.instructions.push_back(text.string());
            if(at(phase,"manual_material_separate_from_displayed_contacts").boolean())d.instructions.push_back("Perform this separate manual source material from the original instructions. The displayed base contacts are not its generated realization.");
            d.typedReportSchema=at(phase,"report_schema");break;}
        case Action::SourceIssueReport:{
            d.label="Stop and choose a printed source repair";d.instructions={"Choose the source diagnosis you are reporting. Stop and explicitly release before practicing its exact repair; no error cause or tempo reduction is inferred."};J::Array values,labels;
            for(const auto& repair:at(harmonicProgram_,"repair_options").array()){values.push_back(at(repair,"id"));labels.push_back(at(repair,"label"));}
            d.typedReportSchema=J::Object{{"type","object"},{"properties",J::Object{{"repair_id",J::Object{{"type","string"},{"enum",values},{"enumLabels",labels},{"learner_label","Printed source diagnosis"}}},{"evidence",J::Object{{"type",J::Array{"string","null"}},{"maxLength",J::fromInteger(4096)},{"learner_label","My manual source evidence"}}}}},{"required",J::Array{"repair_id","evidence"}},{"additionalProperties",false}};break;}
        case Action::SourceRepairReport:{
            d.label="Report the exact separate source repair";const auto& repairs=at(harmonicProgram_,"repair_options").array();const auto found=std::find_if(repairs.begin(),repairs.end(),[this](const auto& r){return at(r,"id")==J(*harmonicRepairDue_);});need(found!=repairs.end(),"HARMONIC_TASK_SOURCE_REPAIR_BINDING");
            for(const auto& text:at(*found,"instructions").array())d.instructions.push_back(text.string());d.typedReportSchema=at(*found,"report_schema");break;}
        case Action::Release:d.label="Report complete hand release";d.fields={reportField(FieldId::HandReleaseReported,"I completely released my hand")};break;
        case Action::OppositeStart:d.label="Repeat the complete unit with the other saved pick start";break;
        case Action::Repeat:d.label="Repeat the full required source traversal";break;
        case Action::Retry:d.label="Retry the same exact source unit";break;
        case Action::Finish:d.label="Finish this reported source unit";d.instructions={"This records your manual source reports only. It grants no observed result, mastery, credit, Practice or parent/book completion."};break;
        case Action::Cancel:d.label="Cancel and explicitly release";break;
        case Action::Restart:d.label="Restart the same source key; retain reports and repair debt";break;
        case Action::AdvancePass:{
            need(sourceContact(policy_),"SOURCE_CONTACT_ROUTE_ACTION_FAMILY");d.label="Choose the next exact saved source route";J::Array values,labels;
            const auto meta=json::parse(source_.trustedMetadataJson());const auto& routes=at(meta,"routes").array();
            std::optional<std::size_t> required;for(std::size_t n=0;n<routes.size();++n)if(at(routes[n],"source_required").boolean()&&!sourceCompletedRoutes_[n]){required=n;break;}
            for(std::size_t n=0;n<routes.size();++n)if(n!=passIndex_&&(!required||n==*required)){values.push_back(J::fromInteger(static_cast<std::int64_t>(n)));labels.push_back(at(routes[n],"label"));}
            d.instructions={"Every required original route must retain its own source criteria and saved pick starts. An available alternative is not the unchanged default realization."};
            d.typedReportSchema=J::Object{{"type","object"},{"properties",J::Object{{"source_route",J::Object{{"type","integer"},{"enum",values},{"enumLabels",labels},{"learner_label","Exact saved source route"}}},{"first_start",J::Object{{"type","integer"},{"enum",J::Array{J::fromInteger(static_cast<int>(Start::Unspecified)),J::fromInteger(static_cast<int>(Start::Down)),J::fromInteger(static_cast<int>(Start::Up))}},{"enumLabels",J::Array{"Source-unspecified","Downstroke","Upstroke"}},{"learner_label","Start saved for the chosen route"}}}}},{"required",J::Array{"source_route","first_start"}},{"additionalProperties",false}};break;
        }
        default:need(false,"HARMONIC_TASK_DESCRIPTOR_ACTION");
        }
        out.push_back(std::move(d));
    }
    return out;
}
void Task::harmonicNextPhaseState(){
    const auto& phases=at(harmonicProgram_,"report_phases").array();
    if(harmonicPhaseIndex_<phases.size()&&static_cast<std::size_t>(integer(at(phases[harmonicPhaseIndex_],"after_source_ordinal")))==nextOrdinal_-1){
        const auto* before=phases[harmonicPhaseIndex_].find("explicit_source_release_before_report");
        if(at(phases[harmonicPhaseIndex_],"manual_material_separate_from_displayed_contacts").boolean()||(sourceContact(policy_)&&before&&before->boolean())){harmonicAfterRelease_=State::SourcePhase;state_=State::Release;}
        else state_=State::SourcePhase;
    }else state_=nextOrdinal_>activeSourceContactCount()?State::Release:State::Traversal;
}
void Task::reportSourcePhase(const Token& token,const J& report){
    fence(token,Action::SourcePhaseReport);const auto& phase=at(harmonicProgram_,"report_phases").array()[harmonicPhaseIndex_];
    bool resolved=sourceContact(policy_)?source_contacts::phaseReportResolved(phase,report):harmonic_contacts::phaseReportResolved(phase,report);
    if(sourceContact(policy_)){
        for(const auto& guard:at(phase,"guards").array())if(at(guard,"kind")==J("saved_equal_literal")){
            const auto found=sourcePassReports_.find(at(guard,"phase").string());
            resolved=resolved&&found!=sourcePassReports_.end()&&at(found->second,at(guard,"field").string().c_str())==at(guard,"value");
        }

        for(const auto& guard:at(phase,"guards").array())
            resolved=resolved&&source_contacts::private_operators::ownedGuard(guard,report,sourcePassReports_);
        if(const auto* requirement=phase.find("owner_requirement")){
            if(*requirement==J("bend_target_held"))resolved=resolved&&sourceBendHeld_;
            else resolved=resolved&&sourcePassReports_.count(requirement->string())!=0;
        }
        if(const auto* action=phase.find("symbolic_owner_action")){
            const auto& kind=at(*action,"kind").string();
            if(kind=="hold")resolved=resolved&&sourceLastEvent_&&sourceExcitationGroup_
                &&*sourceLastEvent_==integer(at(*action,"owner_event_ordinal"))
                &&*sourceExcitationGroup_==integer(at(*action,"excitation_group_ordinal"));
            else if(kind!="explicit_silence"&&at(*action,"new_pick_attack")==J(false))
                resolved=resolved&&sourceLastEvent_&&sourceExcitationGroup_
                &&*sourceLastEvent_==integer(at(*action,"preceding_event_ordinal"))
                &&*sourceExcitationGroup_==integer(at(*action,"excitation_group_ordinal"));
        }
        // A six-note realization belongs to this owner and its start pair. All
        // pitch metadata comes from the exact source position-domain tuple.
        if(const auto* effect=phase.find("owner_effect");effect&&*effect==J("authored_phrase")&&resolved){
            const auto& chosen=at(report,"chosen_contacts");
            need(sourceOwnedChoice_.null()||sourceOwnedChoice_==chosen,"SOURCE_OWNED_PHRASE_CANNOT_CHANGE_BETWEEN_STARTS");
            const auto& domain=at(at(harmonicProgram_,"authored_phrase_contract"),"position_contact_domain").array();
            std::vector<source_contacts::Cue> candidate;
            for(std::size_t i=0;i<chosen.array().size();++i){const auto& choice=chosen.array()[i];
                const auto match=std::find_if(domain.begin(),domain.end(),[&](const J& d){return at(d,"string")==at(choice,"string")&&at(d,"fret")==at(choice,"fret")&&at(d,"note")==at(choice,"note");});
                need(match!=domain.end(),"SOURCE_OWNED_POSITION_TUPLE");
                source_contacts::Atom a{};a.sourceOrdinal=i+1;a.stringLabel=at(choice,"string").string();a.kind="learner_owned_source_domain_contact";a.spelling=at(*match,"note").string();a.attack="source_continuous_alternate_pick";a.annotationsJson=json::stringify(J::Object{{"Deg",at(*match,"degree")}});
                a.stringLowToHigh=a.stringLabel=="E"?1:a.stringLabel=="A"?2:a.stringLabel=="D"?3:a.stringLabel=="G"?4:a.stringLabel=="B"?5:6;
                a.physicalFret=integer(at(choice,"fret"));a.soundingFret=a.physicalFret;a.midi=integer(at(*match,"midi"));if(!at(choice,"chosen_finger").null())a.finger=integer(at(choice,"chosen_finger"));a.picked=true;a.audible=true;
                a.sourceFactsJson=json::stringify(J::Object{{"degree",at(*match,"degree")},{"learner_owned_finger",true}});
                candidate.push_back({sourceKey(),source_.sourceIdentity(),source_.sourceRecordSha256(),passIndex_,i+1,{a},false});
            }
            sourceOwnedChoice_=chosen;sourceOwnedContacts_=std::move(candidate);
            for(auto& p:harmonicProgram_.object()["report_phases"].array())
                if(integer(at(p,"after_source_ordinal"))==2)p.object()["after_source_ordinal"]=J::fromInteger(6);
        }
        const auto* used=report.find("reported_manual_bpm");
        if(used&&!used->null()){need(integer(*used)>0,"SOURCE_CONTACT_REPORTED_TEMPO_POSITIVE");need(!sourceRetainedTempoCeiling_||integer(*used)<=*sourceRetainedTempoCeiling_,"SOURCE_CONTACT_RETRY_RETAINS_TEMPO_CEILING");sourceReportedBpm_=integer(*used);}
        if(const auto* policy=harmonicProgram_.find("tempo_policy");policy&&!policy->null()){
            const auto* errors=report.find("source_errors");const auto* issue=report.find("source_issue");
            if(errors||issue){
                // Unknown quality remains unresolved; it is not evidence of two
                // errors or a source diagnosis that mandates a tempo repair.
                const bool known=errors&&!errors->null()&&issue&&!issue->null()&&*issue!=J("unknown");
                bool debt=false;resolved=resolved&&known;
                if(errors&&!errors->null())debt=debt||integer(*errors)>=integer(at(*policy,"reported_error_threshold"));
                if(issue&&!issue->null())for(const auto& trigger:at(*policy,"immediate_issue_triggers").array())debt=debt||*issue==trigger;
                if(issue&&*issue==J("error")){++errors_;debt=debt||errors_>=2;}if(issue&&*issue==J("clean"))cleanLoops_++;else cleanLoops_=0;
                if(debt){sourceTempoRepairDebt_=true;harmonicRepairDue_=policy->find("repair_id")?at(*policy,"repair_id").string():"source_4_6_reduction";if(policy->find("stop_issue")&&issue&&*issue==at(*policy,"stop_issue"))harmonicRepairDue_=at(*policy,"stop_repair_id").string();if(const auto* map=policy->find("repair_by_issue");map&&issue&&issue->isString()){if(const auto* id=map->find(issue->string()))harmonicRepairDue_=id->string();}resolved=false;}
                if(!issue||*issue!=J("clean"))resolved=false;
            }
        }
        for(const auto& guard:at(phase,"guards").array())if(at(guard,"kind")==J("source_tempo_progression")&&resolved){
            const int prior=integer(at(report,at(guard,"previous_field").string().c_str())),now=integer(at(report,at(guard,"new_field").string().c_str()));
            need(!sourceTempoRepairDebt_&&!harmonicRepairDue_,"SOURCE_CONTACT_TEMPO_ADVANCEMENT_REPAIR_DEBT");need(!sourceReportedBpm_||prior==*sourceReportedBpm_,"SOURCE_CONTACT_PROGRESSION_BINDS_PRIOR_REPORT");need(!sourceRetainedTempoCeiling_||prior<=*sourceRetainedTempoCeiling_,"SOURCE_CONTACT_PROGRESSION_RETAINS_CEILING");
            sourceReportedBpm_=now;if(sourceRetainedTempoCeiling_)sourceRetainedTempoCeiling_=now;
        }

        if(resolved){
            if(const auto* effect=phase.find("owner_effect")){
                if(*effect==J("bend_target_held"))sourceBendHeld_=true;
                if(*effect==J("bend_contact_released"))sourceBendHeld_=false;
            }
            if(const auto* action=phase.find("symbolic_owner_action")){
                if(at(*action,"kind")==J("explicit_silence")){sourceExcitationGroup_.reset();sourceLastEvent_.reset();}
                else if(at(*action,"kind")!=J("hold")){sourceExcitationGroup_=integer(at(*action,"excitation_group_ordinal"));sourceLastEvent_=integer(at(*action,"event_ordinal"));}
            }
        }
        sourcePassReports_[at(phase,"id").string()]=report;
    }
    record(Action::SourcePhaseReport,"manual source criterion "+at(phase,"id").string()+(resolved?" reported met":" unresolved; explicit release and retry required"),{},json::stringify(report));
    if(!resolved){harmonicPhaseUnresolved_=true;cancelledRelease_=true;state_=State::Release;return;}
    ++harmonicPhaseIndex_;harmonicPhaseUnresolved_=false;
    const auto* explicitRelease=phase.find("explicit_source_release_after_report");
    if(at(phase,"manual_material_separate_from_displayed_contacts").boolean()||(sourceContact(policy_)&&explicitRelease&&explicitRelease->boolean())){
        const auto& phases=at(harmonicProgram_,"report_phases").array();harmonicAfterRelease_=harmonicPhaseIndex_<phases.size()?State::SourcePhase:State::Review;state_=State::Release;
        if(sourceContact(policy_))harmonicAfterRelease_=sourceStateAfterPhase();
    }else harmonicNextPhaseState();
}
void Task::reportHarmonicSourceIssue(const Token& token,const std::string& repairId,const J& evidence){
    fence(token,Action::SourceIssueReport);need(harmonic(policy_),"HARMONIC_TASK_SOURCE_ISSUE_FAMILY");
    const auto& repairs=at(harmonicProgram_,"repair_options").array();need(std::any_of(repairs.begin(),repairs.end(),[&](const auto& repair){return at(repair,"id")==J(repairId);}),"HARMONIC_TASK_LITERAL_SOURCE_REPAIR_ID");
    need(evidence.null()||evidence.isString(),"HARMONIC_TASK_SOURCE_EVIDENCE_TYPE");need(evidence.null()||manual_procedure_graph_support::utf8TextLength(evidence.string())<=4096,"HARMONIC_TASK_SOURCE_EVIDENCE_BOUND");
    if(sourceContact(policy_)&&harmonicProgram_.find("private_operator_version")&&(repairId=="source_4_6_reduction"||repairId=="source_4_6_or_isolate"))sourceTempoRepairDebt_=true;
    harmonicRepairDue_=repairId;chosenSessionComplete_=false;cancelledRelease_=true;state_=State::Release;
    record(Action::SourceIssueReport,"reported source diagnosis; stop and owned release before literal repair",{},json::stringify(J::Object{{"repair_id",repairId},{"evidence",evidence}}));
}
void Task::reportSourceRepair(const Token& token,const J& report){
    fence(token,Action::SourceRepairReport);const auto& repairs=at(harmonicProgram_,"repair_options").array();const auto found=std::find_if(repairs.begin(),repairs.end(),[this](const auto& repair){return at(repair,"id")==J(*harmonicRepairDue_);});need(found!=repairs.end(),"HARMONIC_TASK_LITERAL_REPAIR_BINDING");
    const bool resolved=sourceContact(policy_)?source_contacts::phaseReportResolved(*found,report):harmonic_contacts::phaseReportResolved(*found,report);
    if(sourceContact(policy_)&&resolved&&(*harmonicRepairDue_=="source_4_6_reduction"||(*harmonicRepairDue_=="source_4_6_or_isolate"&&at(report,"repair_choice")==J("reduce_4_6")))){
        const int prior=integer(at(report,"previous_reported_bpm")),now=integer(at(report,"reported_new_bpm"));
        need(!sourceReportedBpm_||prior==*sourceReportedBpm_,"SOURCE_CONTACT_REDUCTION_BINDS_ACTUAL_PRIOR_REPORT");
        need(!sourceRetainedTempoCeiling_||now<=*sourceRetainedTempoCeiling_,"SOURCE_CONTACT_REPAIR_CANNOT_RAISE_RETAINED_CEILING");sourceReportedBpm_=now;sourceRetainedTempoCeiling_=now;
    }
    record(Action::SourceRepairReport,"separate literal source repair reported; explicit release remains required",{},json::stringify(report));
    harmonicRepairClearsAfterRelease_=resolved;cancelledRelease_=true;state_=State::Release;
}
View Task::view() const {
    Coverage covered;
    covered.chosenBranchRequiredPassesAndBothStartsReported = chosenSessionComplete_;
    covered.printedPassProgressionReported = baseProgressionReported_;
    covered.restoredPulseReported = chosenSessionComplete_ && branch_ == Branch::RestoredPulse;
    covered.externalAdvancementConditionsReported = advancementReported();
    if(harmonic(policy_)){covered.remainingManualObligations={"Source-null fingers, rhythms, pick starts and all sounding gates/clocks remain unspecified.","Other source units, changed material, drones, recordings, separate-day/session and parent/book/mastery obligations remain manual broader duties."};}
    else if(physical(policy_)) {
        for(const auto& duty:policy_.sourceDuties)if(!includes(sourcePracticeReports_,duty.duty))covered.remainingManualObligations.push_back(duty.label+" remains a separate manual source report.");
        covered.remainingManualObligations.push_back(piecewise(policy_)?"Saved MIDI is retained encoding with no printed octave labels; sounding gates and clocks remain unknown. Unselected rhythms, descending-first options, other modules and full linked circuits are separate manual source duties.":"The fixed cell/module has unknown pitch and sounding gates. Full routes, missing or held siblings, partial selections and linked circuits are not generated by this row.");
        if(policy_.approximateThreeQuarters)covered.remainingManualObligations.push_back("The source approximate 75-percent prior-tempo instruction remains a learner-chosen manual relation; no tolerance, BPM or clock is supplied.");
        covered.remainingManualObligations.push_back("Reports describe manual source practice only; no whole-child, parent, book, mastery, Practice or acoustic claim is established.");
    } else covered.remainingManualObligations.push_back("Other exercises in the printed 12-exercise set remain outside this row's traversal reports.");
    if (policy_.oneModePerSession)
        covered.remainingManualObligations.push_back("Other printed mode and one-mode-per-session rule require separate manual reports.");
    if (policy_.rotationAcrossSessions || policy_.restoreAfterStable || policy_.restoreAfterAdvancement)
        covered.remainingManualObligations.push_back("Triplet/quintuplet source pulse definitions and cross-session restoration/rotation remain manual and untimed.");
    if (!advancementReported() && policy_.advancementNeedsTwoDays)
        covered.remainingManualObligations.push_back("Source full-set, required route/start/mode, and two-separate-day advancement reports remain external.");
    if (!policy_.extensions.empty())
        covered.remainingManualObligations.push_back("Optional post-mastery alternatives have separate instructions; no alternative native contacts are supplied.");
    if (policy_.previousLevel && !initialTempoOffsetReported_)
        covered.remainingManualObligations.push_back("Prior clean tempo and the printed starting-tempo offset have not been fully reported.");
    return {state_, revision_, passIndex_, nextOrdinal_, branch_, rhythm_, start_, state_ == State::Release, state_ == State::Boundary,
        reductionDue_||sourceTempoRepairDebt_, oppositeReported_, cleanLoops_, errors_, sourceContact(policy_)?sourceReportedBpm_:bpm_, plannedBpm_, std::move(covered),harmonicPhaseIndex_,harmonicPhaseUnresolved_,harmonicRepairDue_};
}
void Task::requireAllowed(Action action) const {
    bool allowed = false;
    const bool reviewed = state_ == State::Review && !pendingLoopReport_;
    switch (action) {
    case Action::Begin: allowed = state_ == State::Setup && !reductionDue_ && !sourceIssueRepairDue_; break;
    case Action::Contact: allowed = state_ == State::Traversal; break;
    case Action::BoundaryReport: allowed = state_ == State::Boundary; break;
    case Action::Release: allowed = state_ == State::Release; break;
    case Action::LoopReport: allowed = state_ == State::Review && pendingLoopReport_; break;
    case Action::OppositeStart: allowed = reviewed && !reductionDue_ && !sourceIssueRepairDue_ && firstReported_ && !oppositeReported_ && start_ == firstStart_; break;
    case Action::Repeat: allowed = reviewed && !reductionDue_ && !sourceIssueRepairDue_ && firstReported_ && oppositeReported_; break;
    case Action::Retry: allowed = reviewed && !reductionDue_ && !sourceIssueRepairDue_; break;
    case Action::AdvancePass: allowed = reviewed && !reductionDue_ && !sourceIssueRepairDue_ && firstReported_ && oppositeReported_ && passIndex_ + 1 < policy_.passes.size(); break;
    case Action::Finish: allowed = reviewed && !reductionDue_ && !sourceIssueRepairDue_ && firstReported_ && oppositeReported_ && passIndex_ + 1 == policy_.passes.size(); break;
    case Action::Cancel: allowed = state_ != State::Cancelled; break;
    case Action::Restart: allowed = state_ == State::Cancelled || state_ == State::Finished; break;
    case Action::SessionReport: allowed = state_ == State::Setup || reviewed || state_ == State::Finished || state_ == State::Cancelled; break;
    case Action::ReduceTempo: allowed = reductionDue_ && (reviewed || state_ == State::Setup || state_ == State::Cancelled); break;
    case Action::PlanIncrease: allowed = policy_.sourceTempoRule && !reductionDue_ && !sourceIssueRepairDue_
        && (physical(policy_)?includes(sourcePracticeReports_,SourceDuty::ThreeCleanRoundTrips):cleanLoops_>=3)
        && (reviewed || state_ == State::Finished); break;
    case Action::ExtensionReport: allowed = state_ == State::Finished && !policy_.extensions.empty(); break;
    case Action::SourcePracticeReport: allowed = physical(policy_) && (state_==State::Setup || reviewed || state_==State::Finished || state_==State::Cancelled);break;
    case Action::SourceIssueReport: allowed=piecewise(policy_)&&(state_==State::Traversal||state_==State::Boundary);break;
    case Action::SourcePhaseReport:case Action::SourceRepairReport:break;
    }
    if(harmonic(policy_)){
        const bool both=at(harmonicProgram_,"requires_both_saved_starts").boolean();
        switch(action){
        case Action::Begin:allowed=state_==State::Setup&&!harmonicRepairDue_;break;
        case Action::Contact:allowed=state_==State::Traversal;break;
        case Action::Release:allowed=state_==State::Release;break;
        case Action::SourcePhaseReport:allowed=state_==State::SourcePhase;break;
        case Action::SourceRepairReport:allowed=harmonicRepairDue_.has_value()&&(state_==State::Cancelled||state_==State::Setup);break;
        case Action::SourceIssueReport:allowed=!harmonicRepairDue_&&(!sourceContact(policy_)||!at(harmonicProgram_,"repair_options").array().empty())&&(state_==State::Traversal||state_==State::SourcePhase||state_==State::Cancelled);break;
        case Action::OppositeStart:allowed=reviewed&&both&&firstReported_&&start_==firstStart_&&!oppositeReported_&&!harmonicRepairDue_;break;
        case Action::Finish:case Action::Repeat:allowed=reviewed&&firstReported_&&(!both||oppositeReported_)&&!harmonicRepairDue_&&(!sourceContact(policy_)||allRequiredSourceRoutesReported());break;
        case Action::AdvancePass:allowed=sourceContact(policy_)&&reviewed&&firstReported_&&(!both||oppositeReported_)&&!harmonicRepairDue_&&source_.sourceRouteCount()>1;break;
        case Action::Retry:allowed=reviewed&&!harmonicRepairDue_;break;
        case Action::Cancel:allowed=state_!=State::Cancelled;break;
        case Action::Restart:allowed=state_==State::Cancelled||state_==State::Finished;break;
        default:allowed=false;break;
        }
    }
    need(allowed, "ORDERED_TASK_ACTION_STATE_OR_SOURCE_DEBT");
}
Token Task::capture(Action action) const { requireAllowed(action); return Token(owner_, revision_, action); }
void Task::fence(const Token& token, Action action) const {
    need(token.owner_ == owner_ && token.revision_ == revision_ && token.action_ == action,
         "ORDERED_TASK_OWNER_REVISION_ACTION_FENCE");
    requireAllowed(action);
}
void Task::record(Action action, const std::string& detail, std::optional<Observation> observation, const std::string& report) {
    need(revision_ < std::numeric_limits<std::uint64_t>::max(), "ORDERED_TASK_REVISION_EXHAUSTED");
    ++revision_;
    history_.push_back({revision_, action, source_.sourceKey(), detail, passIndex_, start_, observation, report});
}
void Task::requireRhythm(const PassOption& option, Rhythm rhythm) const {
    need(includes(option.rhythms, rhythm), "ORDERED_TASK_RHYTHM_NOT_PRINTED_FOR_PASS");
}
void Task::startTraversal() {
    if(harmonic(policy_)){selectedReference_.reset();harmonicPhaseIndex_=0;harmonicPhaseUnresolved_=false;harmonicAfterRelease_.reset();if(sourceContact(policy_)){sourcePassReports_.clear();sourceBendHeld_=false;sourceExcitationGroup_.reset();sourceLastEvent_.reset();}}
    else selectedReference_ = source_.projection(neutral(start_));
    nextOrdinal_ = 1; state_ = State::Traversal; pendingLoopReport_ = false;
    if(sourceContact(policy_))harmonicNextPhaseState();
}
void Task::begin(const Token& token, const SetupReport& report) {
    fence(token, Action::Begin);
    for (const auto c : {report.sourceSetupRead, report.onePrintedSetChosen, report.printedModeChosen, report.stableLandings}) requireClaim(c);
    need(report.sourceSetupRead == Claim::Yes && report.onePrintedSetChosen == Claim::Yes
         && (!policy_.oneModePerSession || report.printedModeChosen == Claim::Yes), "ORDERED_TASK_SOURCE_SETUP_REPORT_REQUIRED");
    if(harmonic(policy_)){const bool saved=at(harmonicProgram_,"requires_both_saved_starts").boolean();need(saved?(report.firstStart==Start::Down||report.firstStart==Start::Up):report.firstStart==Start::Unspecified,"HARMONIC_TASK_EXACT_SAVED_OR_UNSPECIFIED_START");need(!report.chosenBpm&&!report.previousCleanBpm&&!report.otherPreviousModeCleanBpm,"HARMONIC_TASK_NO_SOURCE_CLOCK_POLICY");}
    else need(report.firstStart == Start::Down || report.firstStart == Start::Up, "ORDERED_TASK_UNKNOWN_START");
    need(!policy_.downStartFirst || report.firstStart == Start::Down, "ORDERED_TASK_PRINTED_DOWN_THEN_UP_START_ORDER");
    need(report.branch == Branch::PrintedPassProgression || report.branch == Branch::RestoredPulse || (physical(policy_) && report.branch==Branch::DisplacementVariation), "ORDERED_TASK_UNKNOWN_BRANCH");
    const bool prior = baseProgressionReported_ || (sessionReport_ && sessionReport_->priorPrintedPassesReported == Claim::Yes);
    std::size_t selectedPass = 0;
    if (report.branch == Branch::RestoredPulse) {
        need((policy_.restoreAfterStable || policy_.restoreAfterAdvancement) && specialPulse(report.rhythm)
             && prior && report.stableLandings == Claim::Yes
             && (!policy_.restoreAfterAdvancement || advancementReported()), "ORDERED_TASK_RESTORED_PULSE_PREREQUISITES");
        selectedPass = policy_.passes.size() - 1;
    } else {
        need(!((policy_.restoreAfterStable || policy_.restoreAfterAdvancement) && specialPulse(report.rhythm)),
             "ORDERED_TASK_STRAIGHT_PASSES_BEFORE_RESTORATION");
    }
    if(report.branch==Branch::DisplacementVariation) {
        need(policy_.groupedBeforeDisplacement&&report.rhythm==Rhythm::StraightSixteenth
            &&includes(sourcePracticeReports_,SourceDuty::GroupedSecure),"PHYSICAL_TASK_GROUPED_SECURE_BEFORE_DISPLACEMENT");
    } else requireRhythm(policy_.passes[selectedPass], report.rhythm);
    for (const auto& number : {report.chosenBpm, report.previousCleanBpm, report.otherPreviousModeCleanBpm})
        need(!number || *number > 0, "ORDERED_TASK_POSITIVE_EXPLICIT_TEMPO");
    if (report.chosenBpm && report.previousCleanBpm && policy_.belowCleanMinimum != 0) {
        int clean = *report.previousCleanBpm;
        if (policy_.slowerOfTwoPreviousModes) {
            need(report.otherPreviousModeCleanBpm.has_value(), "ORDERED_TASK_SLOWER_PREVIOUS_MODES_NEEDS_BOTH_REPORTS");
            clean = std::min(clean, *report.otherPreviousModeCleanBpm);
        }
        const auto drop = static_cast<std::int64_t>(clean) - *report.chosenBpm;
        need(drop >= policy_.belowCleanMinimum && drop <= policy_.belowCleanMaximum, "ORDERED_TASK_SOURCE_INITIAL_TEMPO_OFFSET");
    }
    need(!report.chosenBpm || !reductionCeilingBpm_ || *report.chosenBpm <= *reductionCeilingBpm_,
         "ORDERED_TASK_RESTART_CANNOT_UNDO_REPORTED_REDUCTION");
    branch_ = report.branch; passIndex_ = selectedPass; firstStart_ = report.firstStart; start_ = firstStart_;
    rhythm_ = report.rhythm; stable_ = report.stableLandings == Claim::Yes; bpm_ = report.chosenBpm;
    setupDone_ = true; firstReported_ = oppositeReported_ = chosenSessionComplete_ = false;
    initialTempoOffsetReported_ = !policy_.previousLevel || (report.chosenBpm && report.previousCleanBpm
        && (!policy_.slowerOfTwoPreviousModes || report.otherPreviousModeCleanBpm));
    const auto data = json::stringify(J::Object{{"branch", branch_ == Branch::PrintedPassProgression ? "PrintedPassProgression" : branch_==Branch::RestoredPulse?"RestoredPulse":"DisplacementVariation"},
        {"rhythm", name(rhythm_)}, {"first_start",firstStart_==Start::Unspecified?J(nullptr):J(firstStart_ == Start::Down ? "D" : "U")},
        {"source_setup_read", reported(report.sourceSetupRead)}, {"one_printed_set_chosen", reported(report.onePrintedSetChosen)},
        {"printed_mode_chosen", reported(report.printedModeChosen)}, {"stable_landings", reported(report.stableLandings)},
        {"chosen_BPM", number(report.chosenBpm)}, {"previous_clean_BPM", number(report.previousCleanBpm)},
        {"other_previous_mode_clean_BPM", number(report.otherPreviousModeCleanBpm)}});
    startTraversal(); record(Action::Begin, name(policy_.passes[passIndex_].pass) + "/" + name(rhythm_) + "/manual source setup reported", {}, data);
}
Cue Task::cue() const {
    need(!harmonic(policy_),"HARMONIC_USE_OPTIONAL_CUE_API");
    need(setupDone_ && (state_ == State::Traversal || state_ == State::Boundary), "ORDERED_TASK_NO_ACTIVE_CONTACT_CUE");
    const auto index = nextOrdinal_ - 1;
    need(selectedReference_ && index < selectedReference_->contacts.size(), "ORDERED_TASK_CUE_EXTENT");
    const auto& contact = selectedReference_->contacts[index];
    const auto pass = policy_.passes[passIndex_].pass;
    if(piecewise(policy_)) {
        const auto route=piecewise_contacts::definition(sourceKey()).routeCue(nextOrdinal_);
        return {nextOrdinal_,contact.stringLowToHigh,contact.fret,contact.finger,contact.midi,contact.spelling,contact.pick,
            route.label,contact.sourceRef,pass,rhythm_,false,route.pressureReleaseBefore,Pause::None,
            ClockAuthority::ManualUntimed,std::nullopt,std::nullopt,route.assignedFrameBefore};
    } else if(physical(policy_)) {
        bool releaseFrame=false,rebuild=false;
        if(index>0) {
            const auto previous=selectedReference_->contacts[index-1].stringLowToHigh;
            const auto current=contact.stringLowToHigh;
            const int low=std::min(previous,current),high=std::max(previous,current);
            const bool offset=low<=4&&high>=5;
            releaseFrame=previous!=current&&policy_.minorGeometryRelease&&(previous==4||current==4||offset);
            rebuild=previous!=current&&policy_.upperGeometryRebuild&&offset;
        }
        const std::size_t group=(policy_.level==18||policy_.level==27)?2U:3U;
        bool accent=pass==Pass::SourceAccent&&index%group==0;
        if(branch_==Branch::DisplacementVariation) {
            const std::size_t g=policy_.level==32?(source_.contactCount()==54?3U:5U):(source_.contactCount()==36?2U:3U);
            accent=index%g==0;
        }
        return {nextOrdinal_,contact.stringLowToHigh,contact.fret,contact.finger,contact.midi,contact.spelling,contact.pick,
            routes_[index<source_.contactCount()/2?0:1],contact.sourceRef,
            branch_==Branch::DisplacementVariation?Pass::SourceDisplacement:pass,rhythm_,accent,releaseFrame,Pause::None,
            ClockAuthority::ManualUntimed,std::nullopt,std::nullopt,rebuild};
    }
    const std::size_t cell = policy_.level == 8 ? 8 : 4;
    const auto local = index % cell + 1;
    bool landing = false;
    if (policy_.level == 2) landing = false;
    else if (policy_.level == 3 || policy_.level == 6 || policy_.level == 10) {
        const bool modeA = headings_.size() == 2 && headings_[1].rfind("MODE A", 0) == 0;
        landing = local == (modeA ? 4U : 2U);
    } else if (policy_.level == 4 || policy_.level == 7 || policy_.level == 11) landing = local == 2 || local == 4;
    else if (policy_.level == 5 || policy_.level == 9) landing = local == 3;
    else if (policy_.level == 8) landing = local == 5;
    const bool accent = (pass == Pass::LandingAccent || pass == Pass::SeparatedAccent
        || pass == Pass::PausedEighthAccent || pass == Pass::ConnectedEighthAccent) && landing;
    Pause pause = Pause::None;
    if ((pass == Pass::SeparatedAccent || pass == Pass::SeparatedEqual) && index > 0 && local == 1)
        pause = Pause::SeparateCell;
    if (pass == Pass::StoppedRelocation && landing) pause = Pause::StopAndRelocate;
    if (pass == Pass::PausedEighthAccent && landing) pause = Pause::OneSubdivisionAtShift;
    bool frameMove = false;
    if (policy_.level >= 8 && index > 0) {
        const auto& previous = selectedReference_->contacts[index - 1];
        frameMove = previous.fret - previous.finger != contact.fret - contact.finger;
    }
    const bool selected = (rhythm_ == Rhythm::StraightSixteenth &&
        (pass == Pass::ConnectedEqual || pass == Pass::ConnectedSixteenth) && policy_.level != 11)
        || (policy_.level == 11 && rhythm_ == Rhythm::StraightEighth && pass == Pass::ConnectedEighthEqual);
    return {nextOrdinal_, contact.stringLowToHigh, contact.fret, contact.finger, contact.midi, contact.spelling,
        contact.pick, routes_[index < source_.contactCount() / 2 ? 0 : 1], contact.sourceRef,
        pass, rhythm_, accent, frameMove, pause,
        selected ? ClockAuthority::SavedSelectedRelativeSlots : ClockAuthority::ManualUntimed,
        selected ? std::optional<music::Span>(music::Span{contact.selectedRelativeHandSlot.onset,contact.selectedRelativeHandSlot.duration}) : std::nullopt, std::nullopt};
}
void Task::confirmContact(const Token& token, std::size_t ordinal, Claim report) {
    fence(token, Action::Contact);
    need(ordinal == nextOrdinal_ && report == Claim::Yes, "ORDERED_TASK_EXACT_NEXT_MANUAL_CONTACT_REPORT");
    record(Action::Contact, std::string(sourceContact(policy_)?"manual source atom ":"manual contact ") + std::to_string(ordinal) + " reported", {},
           json::stringify(J::Object{{"ordinal", J::fromInteger(static_cast<std::int64_t>(ordinal))}, {sourceContact(policy_)?"source_atom_duty_acknowledged":"manually_played", "Yes"}}));
    ++nextOrdinal_;
    if(harmonic(policy_)){harmonicNextPhaseState();return;}
    if (nextOrdinal_ > source_.contactCount()) state_ = State::Release;
    else {
        const auto next = cue();
        if (next.releaseAndRelocateBefore || next.rebuildAssignedFingeringBefore || next.pauseBefore != Pause::None) state_ = State::Boundary;
    }
}
void Task::reportBoundary(const Token& token, const BoundaryReport& report) {
    fence(token, Action::BoundaryReport);
    for (const auto c : {report.pressureReleased, report.wholeFrameRelocated, report.sourcePauseOrSeparationReported}) requireClaim(c);
    const auto next = cue();
    need(!next.releaseAndRelocateBefore || (report.pressureReleased == Claim::Yes && report.wholeFrameRelocated == Claim::Yes),
         "ORDERED_TASK_SOURCE_SHIFT_RELEASE_RELOCATE_REPORT_REQUIRED");
    need(!next.rebuildAssignedFingeringBefore||report.wholeFrameRelocated==Claim::Yes,"PHYSICAL_TASK_ASSIGNED_FINGERING_REBUILD_REPORT_REQUIRED");
    need(next.pauseBefore == Pause::None || report.sourcePauseOrSeparationReported == Claim::Yes,
         "ORDERED_TASK_SOURCE_PAUSE_SEPARATION_REPORT_REQUIRED");
    state_ = State::Traversal;
    record(Action::BoundaryReport, "manual source boundary before ordinal " + std::to_string(nextOrdinal_)
        + (next.releaseAndRelocateBefore ? ": pressure released and whole frame relocated" : "")
        + (next.pauseBefore != Pause::None ? ": source pause/separation reported" : ""), {},
        json::stringify(J::Object{{"pressure_released", reported(report.pressureReleased)},
            {"whole_frame_relocated", reported(report.wholeFrameRelocated)},
            {"source_pause_or_separation_reported", reported(report.sourcePauseOrSeparationReported)}}));
}
void Task::release(const Token& token, Claim report) {
    fence(token, Action::Release);
    need(report == Claim::Yes, "ORDERED_TASK_COMPLETE_HAND_RELEASE_REPORT_REQUIRED");
    if(harmonic(policy_)){
        sourceBendHeld_=false;sourceExcitationGroup_.reset();sourceLastEvent_.reset();
        if(harmonicRepairClearsAfterRelease_){harmonicRepairDue_.reset();harmonicRepairClearsAfterRelease_=false;if(sourceContact(policy_))sourceTempoRepairDebt_=false;}
        if(cancelledRelease_){state_=State::Cancelled;cancelledRelease_=false;pendingLoopReport_=false;harmonicAfterRelease_.reset();}
        else {state_=harmonicAfterRelease_.value_or(State::Review);harmonicAfterRelease_.reset();pendingLoopReport_=false;if(state_==State::Review){if(start_==firstStart_)firstReported_=true;else oppositeReported_=true;
            if(sourceContact(policy_)&&firstReported_&&(!at(harmonicProgram_,"requires_both_saved_starts").boolean()||oppositeReported_))sourceCompletedRoutes_[passIndex_]=true;
        }}
    }
    else if (cancelledRelease_) { state_ = State::Cancelled; cancelledRelease_ = false; pendingLoopReport_ = false; }
    else { state_ = State::Review; pendingLoopReport_ = true; }
    record(Action::Release, "complete hand release manually reported", {}, "{\"complete_hand_release\":\"Yes\"}");
}
void Task::reportLoop(const Token& token, const LoopReport& report) {
    fence(token, Action::LoopReport); requireClaim(report.landingsStable);
    const auto observation = report.observation;
    need(observation != Observation::Unknown && observation >= Observation::Clean && observation <= (piecewise(policy_)?Observation::PickReset:physical(policy_)?Observation::GeometryError:Observation::Squeak),
         "ORDERED_TASK_KNOWN_MANUAL_OBSERVATION_REQUIRED");
    need(!physical(policy_) || observation<=Observation::RisingTension || observation>=Observation::UnevenPulse,"PHYSICAL_TASK_SOURCE_OBSERVATION_SCOPE");
    need(observation != Observation::NoisyGap || (policy_.level >= 5 && policy_.level <= 7), "ORDERED_TASK_GAP_OBSERVATION_OUTSIDE_SOURCE_FAMILY");
    need(observation != Observation::LateLanding || policy_.level >= 8, "ORDERED_TASK_SHIFT_OBSERVATION_OUTSIDE_SOURCE_FAMILY");
    need(observation != Observation::Slide || policy_.level >= 9, "ORDERED_TASK_SLIDE_OBSERVATION_OUTSIDE_SOURCE_FAMILY");
    need(observation != Observation::Squeak || policy_.level == 8 || policy_.level >= 10, "ORDERED_TASK_SQUEAK_OBSERVATION_OUTSIDE_SOURCE_FAMILY");
    need(observation<Observation::UnevenPulse||physical(policy_),"PHYSICAL_TASK_SOURCE_OBSERVATION_FAMILY");
    need(observation!=Observation::UnevenPulse||policy_.sourceTempoRule,"PHYSICAL_TASK_NO_SOURCE_PULSE_REDUCTION_RULE");
    need(observation!=Observation::DraggedShiftNoise||policy_.sourceTempoRule,"PHYSICAL_TASK_NO_SOURCE_SHIFT_REDUCTION_RULE");
    need(observation!=Observation::CrossingAccent||policy_.level==16||policy_.level==17||policy_.level==25||policy_.level==26,"PHYSICAL_TASK_CROSSING_ACCENT_SOURCE");
    need(observation!=Observation::GeometryError||policy_.sourceGeometryObservation,"PHYSICAL_TASK_GEOMETRY_SOURCE");
    if(piecewise(policy_))need(observation==Observation::Clean||observation==Observation::Error||observation==Observation::RisingTension||observation==Observation::DraggedShiftNoise||observation==Observation::WrongPosition||observation==Observation::PickReset||(policy_.level==34&&(observation==Observation::LostKeyCenter||observation==Observation::EarlyShift)),"PIECEWISE_TASK_SOURCE_OBSERVATION");
    stable_ = report.landingsStable == Claim::Yes;
    if (observation == Observation::Clean) { ++cleanLoops_; }
    else {
        cleanLoops_ = 0; ++errors_; plannedBpm_.reset();
        sourcePracticeReports_.erase(std::remove(sourcePracticeReports_.begin(),sourcePracticeReports_.end(),SourceDuty::ThreeCleanRoundTrips),sourcePracticeReports_.end());
        if (policy_.sourceTempoRule && (observation == Observation::RisingTension || errors_ >= 2
            || (physical(policy_) && !piecewise(policy_) && observation>=Observation::UnevenPulse))) reductionDue_ = true;
        if(piecewise(policy_))sourceIssueDebt(observation);
    }
    if (start_ == firstStart_) firstReported_ = true; else oppositeReported_ = true;
    pendingLoopReport_ = false;
    record(Action::LoopReport, "learner loop observation; no observed-performance claim", observation,
        json::stringify(J::Object{{"observation", J::fromInteger(static_cast<int>(observation))},
            {"landings_stable", reported(report.landingsStable)}}));
}
void Task::sourceIssueDebt(Observation observation) {
    need(piecewise(policy_),"PIECEWISE_TASK_ISSUE_POLICY");
    if(observation==Observation::DraggedShiftNoise){sourceNoiseRepairDue_=true;reductionDue_=true;sourceIssueRepairDue_=SourceDuty::NoisePressureThumbRepair;}
    else if(observation==Observation::RisingTension){sourceNarrowingRepairDue_=true;reductionDue_=true;sourceIssueRepairDue_=SourceDuty::ShortenedRouteRepair;}
    else if(observation==Observation::LostKeyCenter)sourceIssueRepairDue_=SourceDuty::LostKeyRootRepair;
    else if(observation==Observation::WrongPosition)sourceIssueRepairDue_=SourceDuty::WrongPositionNamingRepair;
    else if(observation==Observation::EarlyShift)sourceIssueRepairDue_=SourceDuty::EarlyShiftAnchorRepair;
    else if(observation==Observation::PickReset)sourceIssueRepairDue_=SourceDuty::ExactCountAirPickingRepair;
    if(errors_>=2&&!sourceNoiseRepairDue_){sourceNarrowingRepairDue_=true;reductionDue_=true;}
    if(sourceIssueRepairDue_)sourcePracticeReports_.erase(std::remove(sourcePracticeReports_.begin(),sourcePracticeReports_.end(),*sourceIssueRepairDue_),sourcePracticeReports_.end());
}
void Task::reportSourceIssue(const Token& token,Observation observation) {
    fence(token,Action::SourceIssueReport);
    need(observation==Observation::Error||observation==Observation::RisingTension||observation==Observation::DraggedShiftNoise||observation==Observation::WrongPosition||observation==Observation::PickReset||(policy_.level==34&&(observation==Observation::LostKeyCenter||observation==Observation::EarlyShift)),"PIECEWISE_TASK_KNOWN_SOURCE_ISSUE");
    ++errors_;cleanLoops_=0;plannedBpm_.reset();sourcePracticeReports_.erase(std::remove(sourcePracticeReports_.begin(),sourcePracticeReports_.end(),SourceDuty::ThreeCleanRoundTrips),sourcePracticeReports_.end());sourceIssueDebt(observation);
    cancelledRelease_=true;state_=State::Release;chosenSessionComplete_=false;
    record(Action::SourceIssueReport,"source issue at ordinal "+std::to_string(nextOrdinal_)+"; stop and explicitly release before source repair",observation,json::stringify(J::Object{{"ordinal",J::fromInteger(static_cast<std::int64_t>(nextOrdinal_))},{"reported_source_issue",J::fromInteger(static_cast<int>(observation))},{"performance_observed",false}}));
}
void Task::oppositeStart(const Token& token) {
    fence(token, Action::OppositeStart);
    start_ = firstStart_ == Start::Down ? Start::Up : Start::Down;
    startTraversal(); record(Action::OppositeStart, "source opposite pick start; whole source route repeated");
}
void Task::repeat(const Token& token) {
    fence(token, Action::Repeat);
    start_ = firstStart_; firstReported_ = oppositeReported_ = false;
    startTraversal(); record(Action::Repeat, "repeat full source route/start pair");
}
void Task::retry(const Token& token) {
    fence(token, Action::Retry);
    if (start_ == firstStart_) firstReported_ = oppositeReported_ = false; else oppositeReported_ = false;
    startTraversal(); record(Action::Retry, "same source key/pass/start full traversal retry; history retained");
}
void Task::advancePass(const Token& token, Pass pass, Rhythm rhythm) {
    fence(token, Action::AdvancePass);
    need(!sourceContact(policy_),"SOURCE_CONTACT_USE_EXACT_ROUTE_API");
    const auto& next = policy_.passes[passIndex_ + 1];
    need(pass == next.pass, "ORDERED_TASK_REQUIRED_PASS_ORDER");
    requireRhythm(next, rhythm);
    need(policy_.level >= 8 || rhythm == rhythm_, "ORDERED_TASK_RHYTHM_ROTATION_IS_ACROSS_SESSIONS");
    need(!specialPulse(rhythm) || !policy_.restoreAfterAdvancement, "ORDERED_TASK_RESTORE_AFTER_SOURCE_ADVANCEMENT_ONLY");
    need(!next.needsReportedStableLandings || stable_, "ORDERED_TASK_CLEAN_LANDINGS_BEFORE_CONNECTED_ROUTE");
    ++passIndex_; rhythm_ = rhythm; start_ = firstStart_; firstReported_ = oppositeReported_ = false;
    startTraversal(); record(Action::AdvancePass, "source next pass " + name(pass) + "/" + name(rhythm));
}
void Task::advanceSourceRoute(const Token& token,std::size_t route,Start start) {
    fence(token,Action::AdvancePass);need(sourceContact(policy_)&&route<source_.sourceRouteCount()&&route!=passIndex_,"SOURCE_CONTACT_EXACT_DIFFERENT_ROUTE");
    const auto meta=json::parse(source_.trustedMetadataJson());const auto& routes=at(meta,"routes").array();
    for(std::size_t n=0;n<routes.size();++n)if(at(routes[n],"source_required").boolean()&&!sourceCompletedRoutes_[n]){need(route==n,"SOURCE_CONTACT_REQUIRED_ROUTE_ORDER_AND_DEBT");break;}
    const auto program=json::parse(source_.phaseProgramJson(route));const bool saved=at(program,"requires_both_saved_starts").boolean();
    need(saved?(start==Start::Down||start==Start::Up):start==Start::Unspecified,"SOURCE_CONTACT_ROUTE_EXACT_START");
    passIndex_=route;harmonicProgram_=program;harmonicSourceAtoms_=json::parse(source_.phaseAtomsJson(route));start_=firstStart_=start;firstReported_=oppositeReported_=false;
    startTraversal();record(Action::AdvancePass,"exact saved source route selected; original required route debts retained",{},json::stringify(J::Object{{"source_route",J::fromInteger(static_cast<std::int64_t>(route))},{"first_start",J::fromInteger(static_cast<int>(start))}}));
}
void Task::finish(const Token& token) {
    fence(token, Action::Finish);
    state_ = State::Finished; chosenSessionComplete_ = true;
    if (branch_ == Branch::PrintedPassProgression) baseProgressionReported_ = true;
    record(Action::Finish, "chosen source-session pass/start traversals manually reported; no full-child or mastery assertion");
}
void Task::cancel(const Token& token) {
    fence(token, Action::Cancel);
    cancelledRelease_ = true; state_ = State::Release; chosenSessionComplete_ = false;
    record(Action::Cancel, "cancel requested; complete manual release still required; safety debt/history retained");
}
void Task::restart(const Token& token) {
    fence(token, Action::Restart);
    state_ = State::Setup; setupDone_ = false; nextOrdinal_ = 1; passIndex_ = 0;
    firstReported_ = oppositeReported_ = pendingLoopReport_ = chosenSessionComplete_ = false;
    selectedReference_.reset();
    if(sourceContact(policy_)){harmonicProgram_=json::parse(source_.phaseProgramJson());harmonicSourceAtoms_=json::parse(source_.phaseAtomsJson());sourceOwnedContacts_.clear();sourceOwnedChoice_=J(nullptr);}
    record(Action::Restart, "same immutable source key/set/mode; prior reports and reduction debt retained");
}
void Task::deactivateForNavigation() {
    need((state_ == State::Setup || state_ == State::Finished || state_ == State::Cancelled)
         && !cancelledRelease_, "ORDERED_TASK_NAVIGATION_REQUIRES_INACTIVE_RELEASED_OWNER");
    need(revision_ < std::numeric_limits<std::uint64_t>::max(), "ORDERED_TASK_REVISION_EXHAUSTED");
    ++revision_;
}
void Task::reportSession(const Token& token, const SessionReport& report) {
    fence(token, Action::SessionReport);
    for (const auto c : {report.priorPrintedPassesReported, report.fullPrintedSetClean, report.bothRoutesClean,
                        report.bothStartsClean, report.bothModesClean}) requireClaim(c);
    std::set<std::string> days;
    for (const auto& day : report.separateDayLabels)
        need(validDate(day) && days.insert(day).second, "ORDERED_TASK_DISTINCT_VALID_MANUALLY_REPORTED_DAYS");
    if (report.nextSessionRhythm) {
        const auto rhythm = *report.nextSessionRhythm;
        need(policy_.rotationAcrossSessions || policy_.restoreAfterStable || policy_.restoreAfterAdvancement,
             "ORDERED_TASK_NO_SOURCE_ROTATION_RULE");
        need(rhythm == Rhythm::StraightSixteenth || specialPulse(rhythm), "ORDERED_TASK_SOURCE_ROTATION_RHYTHM");
    }
    sessionReport_ = report;
    J::Array labels;
    for (const auto& day : report.separateDayLabels) labels.emplace_back(day);
    record(Action::SessionReport, "external set/route/start/mode/day/rotation conditions manually reported; no parent/book/mastery assertion", {},
        json::stringify(J::Object{{"prior_printed_passes_reported", reported(report.priorPrintedPassesReported)},
            {"full_printed_set_clean", reported(report.fullPrintedSetClean)}, {"both_routes_clean", reported(report.bothRoutesClean)},
            {"both_starts_clean", reported(report.bothStartsClean)}, {"both_modes_clean", reported(report.bothModesClean)},
            {"separate_day_labels", std::move(labels)},
            {"next_session_rhythm", report.nextSessionRhythm ? J(name(*report.nextSessionRhythm)) : J(nullptr)}}));
}
void Task::reportSourcePractice(const Token& token,SourceDuty duty,Claim performed,const BoundaryReport& boundary) {
    fence(token,Action::SourcePracticeReport);requireClaim(performed);
    for(const auto c:{boundary.pressureReleased,boundary.wholeFrameRelocated,boundary.sourcePauseOrSeparationReported})requireClaim(c);
    const auto found=std::find_if(policy_.sourceDuties.begin(),policy_.sourceDuties.end(),[duty](const auto& d){return d.duty==duty;});
    need(found!=policy_.sourceDuties.end(),"PHYSICAL_TASK_DUTY_NOT_IN_SOURCE_POLICY");
    need(performed==Claim::Yes&&(!found->needsRelease||(boundary.pressureReleased==Claim::Yes&&(piecewise(policy_)||boundary.wholeFrameRelocated==Claim::Yes))),"PHYSICAL_TASK_EXPLICIT_EXTERNAL_PRACTICE_AND_RELEASE");
    need((duty!=SourceDuty::NeighboringRungs&&duty!=SourceDuty::PausedCircuit)||boundary.sourcePauseOrSeparationReported==Claim::Yes,"PHYSICAL_TASK_EXTERNAL_SOURCE_PAUSE_REQUIRED");
    need(duty!=SourceDuty::ThreeCleanRoundTrips||!reductionDue_,"PHYSICAL_TASK_CLEAN_ROUTE_REPORT_CANNOT_BYPASS_REDUCTION");
    need(duty!=SourceDuty::ThreeCleanRoundTrips||!sourceIssueRepairDue_,"PIECEWISE_TASK_CLEAN_REPORT_CANNOT_BYPASS_SOURCE_REPAIR");
    if(piecewise(policy_)&&duty==SourceDuty::ShortenedRouteRepair&&(sourceNarrowingRepairDue_||sourceIssueRepairDue_==duty))
        need(boundary.sourcePauseOrSeparationReported==Claim::Yes,"PIECEWISE_TASK_EXPLICIT_STOP_SHORTER_SOURCE_REPAIR");
    if(piecewise(policy_)&&duty==SourceDuty::ShortenedRouteRepair&&sourceNarrowingRepairDue_) {
        need(!sourceNoiseRepairDue_,"PIECEWISE_TASK_NOISY_SHIFT_REQUIRES_PRINTED_REDUCTION");
        need(boundary.sourcePauseOrSeparationReported==Claim::Yes,"PIECEWISE_TASK_STOP_AND_SHORTER_SOURCE_REPAIR_REPORT");
        reductionDue_=false;sourceNarrowingRepairDue_=false;errors_=cleanLoops_=0;plannedBpm_.reset();
    }
    if(sourceIssueRepairDue_&&duty==*sourceIssueRepairDue_)sourceIssueRepairDue_.reset();
    if(!includes(sourcePracticeReports_,duty))sourcePracticeReports_.push_back(duty);
    record(Action::SourcePracticeReport,"separate source practice manually reported; no generated external realization or observed result",{},
        json::stringify(J::Object{{"source_duty",J::fromInteger(static_cast<int>(duty))},{"performed_reported","Yes"},
            {"pressure_released",reported(boundary.pressureReleased)},{"whole_frame_relocated",reported(boundary.wholeFrameRelocated)},
            {"source_pause_reported",reported(boundary.sourcePauseOrSeparationReported)},{"external_contacts_generated",false}}));
}
void Task::reduceTempo(const Token& token, int drop, Claim applied) {
    fence(token, Action::ReduceTempo);
    need(drop >= 4 && drop <= 6 && applied == Claim::Yes, "ORDERED_TASK_SOURCE_FOUR_TO_SIX_BPM_REDUCTION_REPORT");
    need(!sourceNoiseRepairDue_||includes(sourcePracticeReports_,SourceDuty::NoisePressureThumbRepair),"PIECEWISE_TASK_NOISE_PRESSURE_THUMB_BEFORE_REDUCTION");
    need(!bpm_ || *bpm_ > drop, "ORDERED_TASK_REDUCTION_WOULD_MAKE_TEMPO_NONPOSITIVE");
    if (bpm_) { bpm_ = *bpm_ - drop; reductionCeilingBpm_ = bpm_; }
    reductionDue_ = false; sourceNoiseRepairDue_=sourceNarrowingRepairDue_=false;errors_ = cleanLoops_ = 0; plannedBpm_.reset();
    sourcePracticeReports_.erase(std::remove(sourcePracticeReports_.begin(),sourcePracticeReports_.end(),SourceDuty::ThreeCleanRoundTrips),sourcePracticeReports_.end());
    record(Action::ReduceTempo, "manual source tempo reduction " + std::to_string(drop) + " BPM reported; no clock changed", {},
        json::stringify(J::Object{{"drop_BPM", J::fromInteger(drop)}, {"applied", "Yes"}, {"reported_result_BPM", number(bpm_)}}));
}
void Task::planIncreaseNextSession(const Token& token, Claim planned) {
    fence(token, Action::PlanIncrease);
    need(planned == Claim::Yes, "ORDERED_TASK_NEXT_SESSION_PLUS_TWO_PLAN_REPORT_REQUIRED");
    need(!bpm_ || *bpm_ <= std::numeric_limits<int>::max() - 2, "ORDERED_TASK_NEXT_TEMPO_OVERFLOW");
    if (bpm_) plannedBpm_ = *bpm_ + 2;
    record(Action::PlanIncrease, "manual +2 BPM next session plan after three reported clean loops; current tempo unchanged", {},
        json::stringify(J::Object{{"increase_BPM", J::fromInteger(2)}, {"planned_next_session", "Yes"}, {"planned_BPM", number(plannedBpm_)}}));
}
ExtensionGuidance Task::extensionGuidance(Extension extension) const {
    need(includes(policy_.extensions, extension), "ORDERED_TASK_EXTENSION_NOT_IN_SOURCE_FAMILY");
    ExtensionGuidance out{extension, {}, {}, false,
        "Separate source-authorized manual guidance only: no altered native contact/pitch/clock realization is supplied."};
    std::vector<int> lines;
    if (extension == Extension::AlternatingModes) lines = {23};
    else {
        lines = {43, 44, 45};
        if (extension == Extension::DistanceP5P8P11) out.positionFrames = {5, 8, 11};
        else if (extension == Extension::DistanceP5P7P10) out.positionFrames = {5, 7, 10};
    }
    for (const auto& line : policy_.sourceLines) if (includes(lines, line.line)) out.sourceLines.push_back(line);
    return out;
}
void Task::reportExtension(const Token& token, Extension extension, Claim mastery) {
    fence(token, Action::ExtensionReport);
    (void)extensionGuidance(extension);
    need(extension != Extension::OtherPositionDistance, "ORDERED_TASK_OTHER_DISTANCE_REQUIRES_EXPLICIT_FRAMES");
    need(mastery == Claim::Yes && advancementReported(), "ORDERED_TASK_EXTENSION_REQUIRES_EXTERNAL_SOURCE_MASTERY_REPORTS");
    record(Action::ExtensionReport, "optional source extension manually planned; no default contact realization shown or changed; no inferred mastery", {},
        json::stringify(J::Object{{"extension", J::fromInteger(static_cast<int>(extension))}, {"source_mastery_reported", "Yes"},
            {"alternative_native_contacts_supplied", false}}));
}
void Task::reportDistanceExtension(const Token& token, const std::vector<int>& frames, Claim mastery) {
    fence(token, Action::ExtensionReport);
    (void)extensionGuidance(Extension::OtherPositionDistance);
    need(mastery == Claim::Yes && advancementReported(), "ORDERED_TASK_EXTENSION_REQUIRES_EXTERNAL_SOURCE_MASTERY_REPORTS");
    need(frames.size() == 3 && frames[0] > 0 && frames[0] < frames[1] && frames[1] < frames[2],
         "ORDERED_TASK_THREE_ASCENDING_POSITION_FRAMES_REQUIRED");
    J::Array values;
    for (const auto frame : frames) values.push_back(J::fromInteger(frame));
    record(Action::ExtensionReport, "manual alternate-distance plan; preserve 1+2+1/code and descending equivalent; no generated alternative pitches", {},
        json::stringify(J::Object{{"extension", "OtherPositionDistance"}, {"ascending_position_frames", std::move(values)},
            {"source_mastery_reported", "Yes"}, {"alternative_native_contacts_supplied", false}}));
}
std::string Task::continuationSourceSha256()const{
    return content::sha256(json::stringify(J::Object{{"format","fathom-contact-source-binding-v1"},{"metadata",source_.trustedMetadataJson()},{"guidance",fullSourceGuidanceJson()},{"policy",contact_snapshot::encode(policy_)},{"legacy_definition",legacyDefinition_.has_value()}}));
}
std::string Task::continuationStateSha256()const{
    J::Object state{{"source_binding_sha256",continuationSourceSha256()}};
    state.emplace("state_",contact_snapshot::encode(state_));
    state.emplace("revision_",contact_snapshot::encode(revision_));
    state.emplace("passIndex_",contact_snapshot::encode(passIndex_));
    state.emplace("nextOrdinal_",contact_snapshot::encode(nextOrdinal_));
    state.emplace("cleanLoops_",contact_snapshot::encode(cleanLoops_));
    state.emplace("errors_",contact_snapshot::encode(errors_));
    state.emplace("firstStart_",contact_snapshot::encode(firstStart_));
    state.emplace("start_",contact_snapshot::encode(start_));
    state.emplace("rhythm_",contact_snapshot::encode(rhythm_));
    state.emplace("branch_",contact_snapshot::encode(branch_));
    state.emplace("setupDone_",contact_snapshot::encode(setupDone_));
    state.emplace("cancelledRelease_",contact_snapshot::encode(cancelledRelease_));
    state.emplace("stable_",contact_snapshot::encode(stable_));
    state.emplace("reductionDue_",contact_snapshot::encode(reductionDue_));
    state.emplace("sourceNoiseRepairDue_",contact_snapshot::encode(sourceNoiseRepairDue_));
    state.emplace("sourceNarrowingRepairDue_",contact_snapshot::encode(sourceNarrowingRepairDue_));
    state.emplace("sourceIssueRepairDue_",contact_snapshot::encode(sourceIssueRepairDue_));
    state.emplace("firstReported_",contact_snapshot::encode(firstReported_));
    state.emplace("oppositeReported_",contact_snapshot::encode(oppositeReported_));
    state.emplace("chosenSessionComplete_",contact_snapshot::encode(chosenSessionComplete_));
    state.emplace("baseProgressionReported_",contact_snapshot::encode(baseProgressionReported_));
    state.emplace("pendingLoopReport_",contact_snapshot::encode(pendingLoopReport_));
    state.emplace("initialTempoOffsetReported_",contact_snapshot::encode(initialTempoOffsetReported_));
    state.emplace("bpm_",contact_snapshot::encode(bpm_));
    state.emplace("plannedBpm_",contact_snapshot::encode(plannedBpm_));
    state.emplace("reductionCeilingBpm_",contact_snapshot::encode(reductionCeilingBpm_));
    state.emplace("sessionReport_",contact_snapshot::encode(sessionReport_));
    state.emplace("routes_",contact_snapshot::encode(routes_));
    state.emplace("headings_",contact_snapshot::encode(headings_));
    state.emplace("history_",contact_snapshot::encode(history_));
    state.emplace("selectedReference_",contact_snapshot::encode(selectedReference_));
    state.emplace("sourcePracticeReports_",contact_snapshot::encode(sourcePracticeReports_));
    state.emplace("harmonicProgram_",contact_snapshot::encode(harmonicProgram_));
    state.emplace("harmonicSourceAtoms_",contact_snapshot::encode(harmonicSourceAtoms_));
    state.emplace("harmonicSourceContracts_",contact_snapshot::encode(harmonicSourceContracts_));
    state.emplace("harmonicPhaseIndex_",contact_snapshot::encode(harmonicPhaseIndex_));
    state.emplace("harmonicPhaseUnresolved_",contact_snapshot::encode(harmonicPhaseUnresolved_));
    state.emplace("harmonicRepairClearsAfterRelease_",contact_snapshot::encode(harmonicRepairClearsAfterRelease_));
    state.emplace("harmonicRepairDue_",contact_snapshot::encode(harmonicRepairDue_));
    state.emplace("harmonicAfterRelease_",contact_snapshot::encode(harmonicAfterRelease_));
    state.emplace("sourcePassReports_",contact_snapshot::encode(sourcePassReports_));
    state.emplace("sourceCompletedRoutes_",contact_snapshot::encode(sourceCompletedRoutes_));
    state.emplace("sourceOwnedContacts_",contact_snapshot::encode(sourceOwnedContacts_));
    state.emplace("sourceOwnedChoice_",contact_snapshot::encode(sourceOwnedChoice_));
    state.emplace("sourceBendHeld_",contact_snapshot::encode(sourceBendHeld_));
    state.emplace("sourceExcitationGroup_",contact_snapshot::encode(sourceExcitationGroup_));
    state.emplace("sourceLastEvent_",contact_snapshot::encode(sourceLastEvent_));
    state.emplace("sourceTempoRepairDebt_",contact_snapshot::encode(sourceTempoRepairDebt_));
    state.emplace("sourceReportedBpm_",contact_snapshot::encode(sourceReportedBpm_));
    state.emplace("sourceRetainedTempoCeiling_",contact_snapshot::encode(sourceRetainedTempoCeiling_));
    return content::sha256(json::stringify(state));
}
} // namespace fathom::tasks::ordered_contacts::manual
