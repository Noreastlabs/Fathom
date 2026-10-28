#include "tasks/PhysicalContactFamily.hpp"
#include "content/StrictJson.hpp"
#include "GeneratedPhysicalContactData.hpp"
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::tasks::physical_contacts {
namespace {
using J=json::Value;
void need(bool good,const char* reason) { if(!good)throw std::invalid_argument(reason); }
bool hex(const char* value) {
    const std::string s(value);return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;
}
const J& at(const J& value,const char* key) {
    need(value.isObject()&&value.find(key),"PHYSICAL_CONTACT_METADATA_FIELD");return *value.find(key);
}
struct Registry final {
    std::vector<std::string> keys;
    std::vector<Definition> definitions;
    std::map<std::string,std::size_t> byKey;
    Registry();
};
const Registry& registry() { static const Registry r;return r; }
const compiled::Row& row(std::size_t index) {
    (void)registry();need(index<std::size(compiled::rows),"PHYSICAL_CONTACT_CLOSED_INDEX");return compiled::rows[index];
}
WorkflowPattern pattern(int level) {
    switch(level) {
    case 16:case 17:case 25:case 26:return WorkflowPattern::FourNoteRoll;
    case 23:case 24:return WorkflowPattern::ThreeNoteRoll;
    case 21:case 22:case 30:case 31:return WorkflowPattern::LinearEighth;
    case 18:case 27:return WorkflowPattern::DiatonicPairs;
    case 19:case 28:return WorkflowPattern::DiatonicTriads;
    case 20:case 29:return WorkflowPattern::FiveModuleCircuit;
    case 32:return WorkflowPattern::PentatonicOddGroups;
    case 33:return WorkflowPattern::PentatonicSkips;
    default:throw std::invalid_argument("PHYSICAL_CONTACT_SOURCE_POLICY_LEVEL");
    }
}
Registry::Registry() {
    need(std::size(compiled::rows)==339&&std::size(compiled::contacts)==18906&&std::size(compiled::policies)==18
        &&hex(compiled::cohortSha)&&hex(compiled::closureSha),"PHYSICAL_CONTACT_CLOSED_SCOPE");
    std::set<std::string> identities;std::size_t offset=0;
    for(std::size_t index=0;index<std::size(compiled::rows);++index) {
        const auto& r=compiled::rows[index];
        need(byKey.emplace(r.key,index).second&&identities.insert(r.identity).second
            &&hex(r.recordSha)&&hex(r.packetSha)&&r.packetLine>0&&r.level>=16&&r.level<=33,
            "PHYSICAL_CONTACT_UNIQUE_ROW_SOURCE_BINDING");
        need(r.begin==offset&&r.count>0&&r.count<=std::size(compiled::contacts)-offset
            &&r.policy==static_cast<std::size_t>(r.level-16)&&std::string(r.down).size()==r.count
            &&std::string(r.up).size()==r.count,"PHYSICAL_CONTACT_EXACT_ROW_RANGE_VARIANTS");
        const auto policy=json::parse(compiled::policies[r.policy]);
        std::int64_t policyLevel=0;need(at(policy,"level").integer(policyLevel)&&policyLevel==r.level,"PHYSICAL_CONTACT_EXACT_LEVEL_POLICY");
        const auto meta=json::parse(r.metadata);
        need(at(meta,"source_key")==J(r.key)&&at(meta,"source_identity")==J(r.identity)
            &&at(meta,"source_record_canonical_sha256")==J(r.recordSha)
            &&at(meta,"selected_projection")==J(r.selectedProjection),"PHYSICAL_CONTACT_METADATA_CLOSURE");
        Rational next;
        for(std::size_t n=0;n<r.count;++n) {
            const auto& c=compiled::contacts[r.begin+n];
            const Rational onset(c.onN,c.onD),duration(c.durN,c.durD);
            need(c.ordinal==n+1&&c.string>=1&&c.string<=6&&c.fret>=0&&c.finger>=1&&c.finger<=4
                &&c.block>0&&c.line>0&&c.column>0&&onset==next&&Rational(0)<duration
                &&json::parse(c.annotations).isObject(),"PHYSICAL_CONTACT_PHYSICAL_FIELDS_AND_RELATIVE_SLOT");
            need(r.down[n]==(n%2?'U':'D')&&r.up[n]==(n%2?'D':'U'),"PHYSICAL_CONTACT_EXACT_UNINTERRUPTED_PICK");
            next=onset+duration;
        }
        need(next==Rational(r.endN,r.endD),"PHYSICAL_CONTACT_SELECTED_END");
        keys.emplace_back(r.key);offset+=r.count;
    }
    need(offset==18906&&identities.size()==339,"PHYSICAL_CONTACT_COMPLETE_ROWS");
}
}
const char* Definition::sourceKey() const { return row(index_).key; }
const char* Definition::sourceIdentity() const { return row(index_).identity; }
const char* Definition::sourceRecordSha256() const { return row(index_).recordSha; }
const char* Definition::packetPath() const { return row(index_).packetPath; }
const char* Definition::packetSha256() const { return row(index_).packetSha; }
int Definition::packetLine() const { return row(index_).packetLine; }
int Definition::level() const { return row(index_).level; }
std::size_t Definition::contactCount() const { return row(index_).count; }
Rational Definition::selectedMetricEnd() const { const auto& r=row(index_);return Rational(r.endN,r.endD); }
const char* Definition::selectedProjection() const { return row(index_).selectedProjection; }
WorkflowPattern Definition::workflowPattern() const { return pattern(level()); }
Cue Definition::contact(std::size_t ordinal,Start start) const {
    const auto& r=row(index_);need(ordinal>0&&ordinal<=r.count,"PHYSICAL_CONTACT_EXACT_ORDINAL");
    need(start==Start::Down||start==Start::Up,"PHYSICAL_CONTACT_EXPLICIT_PICK_START");
    const auto& c=compiled::contacts[r.begin+ordinal-1];
    return {r.key,r.identity,r.recordSha,ordinal,c.string,c.fret,c.finger,c.label,
        std::string(1,(start==Start::Down?r.down:r.up)[ordinal-1]),c.annotations,c.block,c.grid,c.line,c.column,
        c.attack,{Rational(c.onN,c.onD),Rational(c.durN,c.durD)},std::nullopt,std::nullopt};
}
void Definition::requireSourceParity(const Cue& c,Start start) const {
    const auto expected=contact(c.ordinal,start);
    need(c.sourceKey==expected.sourceKey&&c.sourceIdentity==expected.sourceIdentity&&c.sourceRecordSha256==expected.sourceRecordSha256
        &&c.ordinal==expected.ordinal&&c.stringLowToHigh==expected.stringLowToHigh&&c.fret==expected.fret&&c.finger==expected.finger
        &&c.stringLabel==expected.stringLabel&&c.pick==expected.pick&&c.annotationsJson==expected.annotationsJson
        &&c.blockIndex==expected.blockIndex&&c.gridColumn==expected.gridColumn&&c.sourceLine==expected.sourceLine
        &&c.sourceColumn1Based==expected.sourceColumn1Based&&c.attackAuthority==expected.attackAuthority
        &&c.selectedRelativeHandSlot.onset==expected.selectedRelativeHandSlot.onset
        &&c.selectedRelativeHandSlot.duration==expected.selectedRelativeHandSlot.duration
        &&!c.midi&&!c.acousticSoundingSpan,"PHYSICAL_CONTACT_SOURCE_PARITY_OR_UNKNOWN_PITCH_GATE");
}
std::string Definition::trustedMetadataJson() const { return row(index_).metadata; }
std::string Definition::trustedSourcePolicyJson() const { return compiled::policies[row(index_).policy]; }
const std::vector<std::string>& keys() { return registry().keys; }
const Definition& definition(const std::string& key) {
    const auto& r=registry();const auto found=r.byKey.find(key);need(found!=r.byKey.end(),"PHYSICAL_CONTACT_UNKNOWN_KEY");
    // Private construction occurs here; the stable handles are held by this closed factory.
    static const auto handles=[] { std::vector<Definition> out;out.reserve(std::size(compiled::rows));
        for(std::size_t i=0;i<std::size(compiled::rows);++i)out.push_back(Definition(i));return out; }();
    return handles[found->second];
}
const char* cohortSha256() { return compiled::cohortSha; }
const char* closureSha256() { return compiled::closureSha; }
std::size_t sourcePolicyCount() { return std::size(compiled::policies); }
} // namespace fathom::tasks::physical_contacts
