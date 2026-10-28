#include "tasks/PhysicalContactFamily.hpp"
#include "content/StrictJson.hpp"
#include <CommonCrypto/CommonDigest.h>
#include <array>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <sstream>

namespace {
namespace F=fathom::tasks::physical_contacts;
using J=fathom::json::Value;
std::size_t checks=0,refusals=0,rows=0,variants=0,contacts=0,unknownPitch=0,unknownGate=0;
void check(bool value,const char* why) {++checks;if(!value)throw std::runtime_error(why);}
const J& at(const J& obj,const char* field) {check(obj.isObject()&&obj.find(field),"SOURCE_FIELD");return *obj.find(field);}
std::int64_t integer(const J& value) {std::int64_t n=0;check(value.integer(n),"SOURCE_EXACT_INTEGER");return n;}
std::string read(const std::filesystem::path& p) {
    std::ifstream input(p,std::ios::binary);check(input.good(),"SOURCE_FILE_OPEN");std::ostringstream b;b<<input.rdbuf();return b.str();
}
std::string sha(const std::string& raw) {
    check(raw.size()<=std::numeric_limits<CC_LONG>::max(),"HASH_BOUND");std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> data{};
    CC_SHA256(raw.data(),static_cast<CC_LONG>(raw.size()),data.data());std::ostringstream o;
    for(const auto c:data)o<<std::hex<<std::setw(2)<<std::setfill('0')<<static_cast<int>(c);return o.str();
}
fathom::Rational rational(const J& q) {check(q.isArray()&&q.array().size()==2,"EXACT_SOURCE_RATIONAL");return fathom::Rational(integer(q.array()[0]),integer(q.array()[1]));}
template<class Function>void refuses(Function&& f) {
    bool refused=false;try{f();}catch(const std::invalid_argument&){refused=true;}
    check(refused,"EXPECTED_PHYSICAL_SOURCE_REFUSAL");++refusals;
}
void mutations(const F::Definition& d) {
    const auto source=d.contact(1,F::Start::Down);
    refuses([&]{(void)d.contact(0,F::Start::Down);});
    refuses([&]{(void)d.contact(d.contactCount()+1,F::Start::Down);});
    refuses([&]{(void)d.contact(1,static_cast<F::Start>(77));});
    auto bad=source;bad.midi=0;refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;bad.acousticSoundingSpan=F::ManualSpan{fathom::Rational(0,1),fathom::Rational(1,4)};refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;++bad.fret;refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;bad.sourceKey="other";refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;++bad.ordinal;refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;bad.annotationsJson="{}";refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;bad.selectedRelativeHandSlot.duration=fathom::Rational(1,1);refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;bad.pick="U";refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    bad=source;++bad.sourceColumn1Based;refuses([&]{d.requireSourceParity(bad,F::Start::Down);});
    d.requireSourceParity(source,F::Start::Down);
}
void proof(const std::filesystem::path& root) {
    const auto cohortRaw=read(root/"Build/manager-resume-r03/unpitched-contact-preparation-r01/cohort.json");
    const auto cohort=fathom::json::parse(cohortRaw);check(sha(cohortRaw)==F::cohortSha256(),"FROZEN_COHORT_EXACT_HASH");
    const auto source=fathom::json::parse(read(root/"Build/manager-resume-r03/unpitched-contact-preparation-r01/shared-source-policies.json"));
    const auto sourceRows=at(cohort,"rows").array();check(sourceRows.size()==339&&F::keys().size()==339&&F::sourcePolicyCount()==18,"CLOSED_DENOMINATORS");
    std::map<std::string,std::vector<J>> packets;
    for(const auto& ref:at(cohort,"source_input_refs").array()) {
        const auto path=at(ref,"path").string();const auto raw=read(root/path);
        check(raw.size()==static_cast<std::size_t>(integer(at(ref,"bytes")))&&sha(raw)==at(ref,"sha256").string(),"FROZEN_PACKET_PIN");
        std::istringstream stream(raw);std::string line;std::vector<J> parsed;
        while(std::getline(stream,line)){check(!line.empty(),"NO_BLANK_SOURCE_RECORD");parsed.push_back(fathom::json::parse(line));}
        check(packets.emplace(path,std::move(parsed)).second,"UNIQUE_PACKET");
    }
    std::set<std::string> keys,identities;std::map<int,std::size_t> levels;std::map<int,const F::Definition*> representatives;
    for(std::size_t i=0;i<sourceRows.size();++i) {
        const auto& row=sourceRows[i];const auto key=at(row,"key").string();const auto& d=F::definition(key);
        const auto& ref=at(row,"ref");const auto& record=packets.at(at(ref,"path").string()).at(static_cast<std::size_t>(integer(at(ref,"jsonl_line"))-1));
        check(F::keys()[i]==key&&keys.insert(key).second&&identities.insert(d.sourceIdentity()).second,"UNIQUE_STABLE_KEY_IDENTITY_ORDER");
        check(key==d.sourceKey()&&at(record,"source_identity").string()==d.sourceIdentity()&&integer(at(record,"level"))==d.level()
            &&sha(fathom::json::stringify(record))==d.sourceRecordSha256()&&at(ref,"path").string()==d.packetPath()
            &&at(ref,"sha256").string()==d.packetSha256()&&integer(at(ref,"jsonl_line"))==d.packetLine(),"EXACT_NATIVE_ROW_SOURCE_BINDING");
        const auto& cs=at(at(record,"implementation"),"ordered_contacts").array();const auto& vs=at(at(record,"implementation"),"relative_variants").array();
        check(cs.size()==d.contactCount()&&vs.size()==2,"CONTACT_VARIANT_COUNTS");
        check(rational(at(at(record,"timing_authority"),"end_q"))==d.selectedMetricEnd()
            &&at(at(record,"timing_authority"),"selected_projection").string()==d.selectedProjection(),"EXACT_SELECTED_METRIC_SCOPE");
        const auto metadata=fathom::json::parse(d.trustedMetadataJson());
        check(at(metadata,"frozen_MIDI").null()&&at(metadata,"acoustic_sounding_span").null()
            &&at(metadata,"full_child_completion")==J(false)&&at(metadata,"runtime_admitted")==J(false)
            &&at(metadata,"source_clock_supplied")==J(false),"EXPLICIT_UNKNOWN_NONCOMPLETION_LIMITS");
        check(at(metadata,"unit_direction_task_steps")==at(at(record,"implementation"),"task_steps")
            &&at(metadata,"unit_instruction_lines")==at(at(record,"source_payload"),"instruction_lines"),"ALL_ROW_PRINTED_SOURCE_DUTIES_RETAINED");
        check(fathom::json::parse(d.trustedSourcePolicyJson())==at(source,"policies").array().at(static_cast<std::size_t>(d.level()-16)),"EXACT_SHARED_SOURCE_POLICY");
        for(const auto& v:vs) {
            const auto start=at(v,"start_stroke").string()=="D"?F::Start::Down:F::Start::Up;
            for(std::size_t n=0;n<cs.size();++n) {
                const auto& original=cs[n];const auto c=d.contact(n+1,start);d.requireSourceParity(c,start);
                check(integer(at(original,"ordinal"))==static_cast<std::int64_t>(c.ordinal)
                    &&integer(at(original,"string_low_to_high"))==c.stringLowToHigh&&integer(at(original,"fret"))==c.fret
                    &&integer(at(original,"finger"))==c.finger&&at(original,"string_label").string()==c.stringLabel,
                    "ALL_CONTACT_PHYSICAL_EQUALITY");
                check(fathom::json::stringify(at(original,"annotations"))==c.annotationsJson
                    &&integer(at(original,"block_index"))==c.blockIndex&&integer(at(original,"grid_column"))==c.gridColumn
                    &&integer(at(original,"source_line"))==c.sourceLine&&integer(at(original,"source_column_1based"))==c.sourceColumn1Based
                    &&at(original,"attack_authority").string()==c.attackAuthority,"ALL_CONTACT_ANNOTATION_LOCATOR_ATTACK_EQUALITY");
                check(rational(at(original,"onset_q"))==c.selectedRelativeHandSlot.onset
                    &&rational(at(original,"duration_q"))==c.selectedRelativeHandSlot.duration
                    &&integer(at(v,"contact_ordinals").array()[n])==static_cast<std::int64_t>(c.ordinal)
                    &&at(v,"strokes").array()[n].string()==c.pick,"ALL_SAVED_VARIANT_AND_RELATIVE_SLOT_EQUALITY");
                check(at(original,"midi").null()&&!c.midi&&!c.acousticSoundingSpan,"EVERY_PITCH_AND_SOUNDING_GATE_UNKNOWN");
                ++contacts;++unknownPitch;++unknownGate;
            }
            check(rational(at(v,"end_q"))==d.selectedMetricEnd(),"VARIANT_ENDPOINT_EQUALITY");++variants;
        }
        ++levels[d.level()];representatives.emplace(d.level(),&d);++rows;
    }
    const std::map<int,std::size_t> expected{{16,11},{17,11},{18,11},{19,10},{20,60},{21,10},{22,11},{23,12},{24,12},{25,12},{26,12},{27,13},{28,13},{29,64},{30,12},{31,13},{32,26},{33,26}};
    check(levels==expected&&packets.size()==18&&unknownPitch==37812&&unknownGate==37812,"COMPLETE_LEVEL_VARIANT_UNKNOWN_COUNTS");
    std::set<F::WorkflowPattern> patterns;
    for(const auto& x:representatives){patterns.insert(x.second->workflowPattern());mutations(*x.second);}
    check(patterns.size()==8,"EIGHT_DISPATCH_PATTERNS_WITH_EIGHTEEN_SOURCE_POLICIES");
    for(const auto& key:{std::string("unknown"),std::string("proposed-printed-l004-set-1-of-9-exercises-001-012-exercise-006-1234"),std::string("proposed-printed-l004-set-2-of-9-exercises-013-024-exercise-016-1341")})
        refuses([&]{(void)F::definition(key);});
}
}
int main(int argc,char** argv) {
    try {check(argc==2,"ROOT_ARGUMENT");proof(argv[1]);
        std::cout<<"{\"result\":\"PASS\",\"rows\":"<<rows<<",\"variants\":"<<variants<<",\"contact_variant_observations\":"<<contacts
            <<",\"unknown_MIDI_observations\":"<<unknownPitch<<",\"unknown_acoustic_gate_observations\":"<<unknownGate
            <<",\"source_policy_groups\":18,\"dispatch_patterns\":8,\"assertions\":"<<checks<<",\"refusals\":"<<refusals
            <<",\"MusicModel_or_player_created\":false,\"source_original_research\":0,\"official_runtime_acceptance_increments\":0}\n";return 0;
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
