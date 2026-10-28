#include "tasks/PhysicalContactFamily.hpp"
#include "content/StrictJson.hpp"
#include "GeneratedSourceWorkflowBlueprints.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <iostream>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>

namespace {
namespace P=fathom::tasks::physical_contacts;
using J=fathom::json::Value;
std::size_t checks=0,refusals=0,sourceLines=0,phaseChoices=0,externalBranches=0;
void need(bool value,const char* why) {++checks;if(!value)throw std::invalid_argument(why);}
const J& at(const J& v,const char* key) {need(v.isObject()&&v.find(key),"BLUEPRINT_FIELD");return *v.find(key);}
std::int64_t integer(const J& v) {std::int64_t n=0;need(v.integer(n),"BLUEPRINT_INTEGER");return n;}
std::string sha(const std::string& raw) {
    std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> data{};CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),data.data());
    std::ostringstream out;for(const auto c:data)out<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(c);return out.str();
}
void validate(const J& blueprint) {
    const auto& policies=at(blueprint,"policies").array();need(policies.size()==18&&integer(at(blueprint,"source_policy_groups"))==18
        &&integer(at(blueprint,"dispatch_templates"))==8&&at(blueprint,"no_owner_execution_or_behavior_equivalence_claim")==J(true),"EXACT_BLUEPRINT_SCOPE");
    std::map<int,const P::Definition*> reps;for(const auto& key:P::keys())reps.emplace(P::definition(key).level(),&P::definition(key));
    const std::map<int,std::size_t> expected{{16,1},{17,1},{18,3},{19,3},{20,3},{21,1},{22,1},{23,1},{24,1},{25,1},{26,1},{27,3},{28,3},{29,3},{30,1},{31,1},{32,2},{33,2}};
    std::set<int> levels;std::set<std::string> patterns;
    for(const auto& item:policies) {
        const auto& tag=at(item,"tag");const auto level=static_cast<int>(integer(at(tag,"level")));
        need(at(tag,"family")==J("physical_contact")&&reps.count(level)&&levels.insert(level).second,"EXACT_UNIQUE_PHYSICAL_POLICY_TAG");
        const auto native=fathom::json::parse(reps.at(level)->trustedSourcePolicyJson());
        need(at(item,"source_context_ref")==at(native,"context_ref"),"BLUEPRINT_EXACT_FROZEN_CONTEXT_PIN");
        const auto& source=at(at(native,"source_context"),"guidance_lines");
        need(sha(fathom::json::stringify(source))==at(item,"full_guidance_sha256").string(),"FULL_SOURCE_GUIDANCE_HASH");
        std::map<std::int64_t,J> byLine;
        for(const auto& line:source.array())need(byLine.emplace(integer(at(line,"line")),line).second,"UNIQUE_NATIVE_SOURCE_LINE");
        for(const auto* field:{"source_rhythm_lines","source_release_safety_lines","source_tempo_progression_lines"})
            for(const auto& line:at(item,field).array()) {
                const auto number=integer(at(line,"line"));need(byLine.count(number)&&byLine.at(number)==line,"EVERY_BLUEPRINT_LINE_EXACT_SOURCE_LITERAL");++sourceLines;
            }
        need(!at(item,"source_rhythm_lines").array().empty()&&!at(item,"source_release_safety_lines").array().empty(),"SOURCE_RHYTHM_RELEASE_DUTIES_PRESENT");
        const auto& phases=at(item,"supported_complete_printed_cell_or_module_choices").array();
        need(phases.size()==expected.at(level),"SOURCE_SPECIFIC_COMPLETE_CELL_PHASE_CHOICES");
        std::set<std::string> ids;
        for(const auto& phase:phases) {
            need(ids.insert(at(phase,"id").string()).second&&at(phase,"active_clock")==J("manual_untimed")
                &&at(phase,"native_contacts")==J("exact frozen printed cell/module ordinals and picks")
                &&at(phase,"selected_stored_relative_slots")==J("trusted data retained; not presented as this phase rhythm"),"NO_SOURCE_GRID_PROMOTION_OR_ALTERNATIVE_REALIZATION");
            for(const auto& number:at(phase,"source_rhythm_duty_refs").array())need(byLine.count(integer(number)),"PHASE_EXACT_SOURCE_DUTY_LOCATOR");
            ++phaseChoices;
        }
        for(const auto& branch:at(item,"external_manual_source_branches").array()) {
            need(at(branch,"generated_realization")==J(false)&&at(branch,"completion_claim")==J("manual external report only; no parent/book/mastery inference"),"EXTERNAL_FULLROUTE_LINK_COMPARISON_NOT_SYNTHESIZED");++externalBranches;
        }
        need(at(item,"fixed_BPM").null()&&at(item,"source_acoustic_gates").null()&&at(item,"performance_observed")==J(false)
            &&at(item,"runtime_admitted")==J(false)&&at(item,"dispatch_template_not_behavior_equivalence")==J(true),"UNKNOWN_CLOCK_ACOUSTICS_AND_INDEPENDENT_GATES");
        patterns.insert(at(item,"dispatch_template").string());
    }
    need(levels.size()==18&&patterns.size()==8,"ALL18_POLICIES_EIGHT_HINT_TEMPLATES");
}
template<class Action>void refuses(Action&& action) {bool rejected=false;try{action();}catch(const std::invalid_argument&){rejected=true;}need(rejected,"EXPECTED_BLUEPRINT_NEGATIVE");++refusals;}
void negative(J original) {
    auto bad=original;bad.object()["policies"].array()[0].object()["fixed_BPM"]=J::fromInteger(90);refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[0].object()["tag"].object()["level"]=J::fromInteger(44);refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[1].object()["tag"]=at(bad.object()["policies"].array()[0],"tag");refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[0].object()["source_context_ref"].object()["sha256"]=J("unknown");refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[0].object()["source_release_safety_lines"].array()[0].object()["text"]=J("changed");refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[0].object()["supported_complete_printed_cell_or_module_choices"].array()[0].object()["active_clock"]=J("selected_grid");refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array()[0].object()["external_manual_source_branches"].array()[0].object()["generated_realization"]=J(true);refuses([&]{validate(bad);});
    bad=original;bad.object()["policies"].array().pop_back();refuses([&]{validate(bad);});
}
}
int main() {
    try {
        const auto original=fathom::json::parse(fathom::tasks::manual_contacts::blueprint_data::json);validate(original);
        const auto lines=sourceLines,phases=phaseChoices,external=externalBranches;negative(original);
        std::cout<<"{\"result\":\"PASS\",\"source_policy_blueprints\":18,\"dispatch_templates\":8,\"exact_source_line_bindings\":"<<lines
            <<",\"supported_manual_phase_choices\":"<<phases<<",\"external_manual_branches\":"<<external
            <<",\"assertions\":"<<checks<<",\"refusals\":"<<refusals<<",\"owner_execution_or_old_QA_replayed\":false,\"MusicModel_created\":false,\"official_runtime_acceptance_increments\":0}\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
