#include "tasks/PiecewiseContactFamily.hpp"
#include "content/StrictJson.hpp"
#include "GeneratedPiecewiseContactData.hpp"
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::tasks::piecewise_contacts {
namespace {
using J=json::Value;
void need(bool b,const char* why) {if(!b)throw std::invalid_argument(why);}
const J& at(const J& j,const char* key) {need(j.isObject()&&j.find(key),"PIECEWISE_REQUIRED_FIELD");return *j.find(key);}
int number(const J& j) {std::int64_t n=0;need(j.integer(n)&&n>=0&&n<=100000,"PIECEWISE_INTEGER");return static_cast<int>(n);}
Rational rational(const J& j) {need(j.isArray()&&j.array().size()==2,"PIECEWISE_RATIONAL");return Rational(number(j.array()[0]),number(j.array()[1]));}
bool hex(const std::string& s) {return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
struct Registry {
    std::vector<J> rows;
    J contexts=json::parse(compiled::contextsJson);
    std::vector<std::string> keys;
    std::map<std::string,std::size_t> indices;
    Registry() {
        need(compiled::rows.size()==17&&contexts.isObject()&&contexts.object().size()==2&&hex(compiled::closureSha),"PIECEWISE_CLOSED17_TWO_CONTEXTS");
        std::set<std::string> identities;std::size_t total=0;
        for(const auto& r:compiled::rows) {
            auto j=json::parse(r.json);const auto& cs=at(j,"contacts").array();const auto& meta=at(j,"metadata");
            need(at(j,"source_key")==J(r.key)&&indices.emplace(r.key,rows.size()).second&&identities.insert(at(j,"source_identity").string()).second&&hex(at(j,"record_sha256").string()),"PIECEWISE_SOURCE_IDENTITY");
            const auto level=number(at(j,"level"));need(level==34||level==35,"PIECEWISE_EXACT_LEVEL");const auto& ctx=at(contexts,std::to_string(level).c_str());need(at(ctx,"context_ref")==at(j,"context_ref")&&at(at(ctx,"source_context"),"level")==at(j,"level"),"PIECEWISE_CONTEXT_BINDING");
            need(at(meta,"source_clock").null()&&at(meta,"source_sounding_gate").null()&&at(meta,"runtime_admitted")==J(false),"PIECEWISE_MANUAL_BOUNDARY");
            Rational next;std::size_t ord=0;
            for(const auto& c:cs) {
                need(number(at(c,"ordinal"))==static_cast<int>(++ord)&&number(at(c,"string_low_to_high"))>=1&&number(at(c,"string_low_to_high"))<=6&&number(at(c,"finger"))>=1&&number(at(c,"finger"))<=4&&number(at(c,"midi"))<=127&&at(c,"acoustic_gate_q").null()&&at(c,"pick_attack")==J(true),"PIECEWISE_FROZEN_CONTACT_TYPES");
                const auto on=rational(at(c,"onset_q")),dur=rational(at(c,"duration_q"));need(on==next&&Rational(0)<dur,"PIECEWISE_RELATIVE_HAND_SLOT");next=on+dur;
            }
            need(next==rational(at(j,"metric_end"))&&at(j,"variants").array().size()==2,"PIECEWISE_END_VARIANTS");
            for(std::size_t start=0;start<2;++start) {
                const auto& v=at(j,"variants").array()[start];const auto& ords=at(v,"ordered_contact_ordinals").array();const auto& picks=at(v,"strokes_by_contact").array();
                need(ords.size()==cs.size()&&picks.size()==cs.size()&&at(v,"pick_start")==J(start==0?"D":"U")&&at(v,"continuous_across_all_internal_boundaries")==J(true),"PIECEWISE_SAVED_VARIANT");
                for(std::size_t n=0;n<cs.size();++n)need(number(ords[n])==static_cast<int>(n+1)&&picks[n]==J((n+start)%2?"U":"D"),"PIECEWISE_CONTINUOUS_PICK");
            }
            const auto& parts=at(at(meta,"route_projection"),"parts").array();std::size_t position=1;
            for(const auto& p:parts){need(number(at(p,"first"))==static_cast<int>(position)&&number(at(p,"last"))>=static_cast<int>(position),"PIECEWISE_ROUTE_PARTITION");position=number(at(p,"last"))+1;}
            need(position==cs.size()+1,"PIECEWISE_ALL_CONTACTS_PARTITIONED");
            keys.emplace_back(r.key);total+=cs.size();rows.push_back(std::move(j));
        }
        need(total==432,"PIECEWISE_432_CONTACTS");
    }
};
const Registry& registry() {static const Registry r;return r;}
const J& row(std::size_t i) {const auto& r=registry();need(i<r.rows.size(),"PIECEWISE_CLOSED_INDEX");return r.rows[i];}
const char* string(const J& j,const char* name) {return at(j,name).string().c_str();}
}
const char* Definition::sourceKey() const {return string(row(index_),"source_key");}
const char* Definition::sourceIdentity() const {return string(row(index_),"source_identity");}
const char* Definition::sourceRecordSha256() const {return string(row(index_),"record_sha256");}
const char* Definition::packetPath() const {return string(at(row(index_),"payload_ref"),"path");}
const char* Definition::packetSha256() const {return string(at(row(index_),"payload_ref"),"sha256");}
int Definition::packetLine() const {return number(at(at(row(index_),"payload_ref"),"jsonl_line"));}
int Definition::level() const {return number(at(row(index_),"level"));}
std::size_t Definition::contactCount() const {return at(row(index_),"contacts").array().size();}
Rational Definition::selectedMetricEnd() const {return rational(at(row(index_),"metric_end"));}
Cue Definition::contact(std::size_t ordinal,Start start) const {
    need(ordinal>0&&ordinal<=contactCount()&&(start==Start::Down||start==Start::Up),"PIECEWISE_EXACT_ORDINAL_START");const auto& c=at(row(index_),"contacts").array()[ordinal-1];const auto& v=at(row(index_),"variants").array()[start==Start::Down?0:1];
    return {{sourceKey(),sourceIdentity(),sourceRecordSha256(),ordinal,number(at(c,"string_low_to_high")),number(at(c,"fret")),number(at(c,"finger")),at(c,"string_label").string(),at(v,"strokes_by_contact").array()[ordinal-1].string(),json::stringify(at(c,"annotations")),number(at(c,"block_index")),number(at(c,"grid_column")),number(at(c,"source_line")),number(at(c,"source_column_1based")),at(c,"attack_authority").string(),{rational(at(c,"onset_q")),rational(at(c,"duration_q"))},number(at(c,"midi")),std::nullopt},at(c,"note_spelling").string(),number(at(c,"degree"))};
}
RouteCue Definition::routeCue(std::size_t ordinal) const {
    need(ordinal>0&&ordinal<=contactCount(),"PIECEWISE_ROUTE_ORDINAL");const auto& p=at(at(row(index_),"metadata"),"route_projection");RouteCue out{{},false,false};
    for(const auto& part:at(p,"parts").array())if(ordinal>=static_cast<std::size_t>(number(at(part,"first")))&&ordinal<=static_cast<std::size_t>(number(at(part,"last"))))out.label=at(part,"label").string();
    for(const auto& b:at(p,"boundaries").array())if(ordinal==static_cast<std::size_t>(number(at(b,"before")))){out.assignedFrameBefore=at(b,"assigned_frame").boolean();out.pressureReleaseBefore=at(b,"pressure_release").boolean();need(at(b,"pause")==J(false),"PIECEWISE_NO_ADDED_PAUSE");}
    need(!out.label.empty(),"PIECEWISE_REQUIRED_SOURCE_PART");return out;
}
void Definition::requireSourceParity(const Cue& actual,Start start) const {
    const auto c=contact(actual.source.ordinal,start);const auto& a=actual.source;const auto& b=c.source;
    need(a.sourceKey==b.sourceKey&&a.sourceIdentity==b.sourceIdentity&&a.sourceRecordSha256==b.sourceRecordSha256&&a.ordinal==b.ordinal&&a.stringLowToHigh==b.stringLowToHigh&&a.fret==b.fret&&a.finger==b.finger&&a.stringLabel==b.stringLabel&&a.pick==b.pick&&a.midi==b.midi&&!a.acousticSoundingSpan&&a.selectedRelativeHandSlot.onset==b.selectedRelativeHandSlot.onset&&a.selectedRelativeHandSlot.duration==b.selectedRelativeHandSlot.duration&&a.annotationsJson==b.annotationsJson&&a.blockIndex==b.blockIndex&&a.gridColumn==b.gridColumn&&a.sourceLine==b.sourceLine&&a.sourceColumn1Based==b.sourceColumn1Based&&a.attackAuthority==b.attackAuthority&&actual.spelling==c.spelling&&actual.degree==c.degree,"PIECEWISE_EXACT_SOURCE_PARITY");
}
std::string Definition::trustedMetadataJson() const {return json::stringify(at(row(index_),"metadata"));}
std::string Definition::trustedContextJson() const {return json::stringify(at(registry().contexts,std::to_string(level()).c_str()));}
const std::vector<std::string>& keys() {return registry().keys;}
const Definition& definition(const std::string& key) {
    const auto& r=registry();const auto found=r.indices.find(key);need(found!=r.indices.end(),"PIECEWISE_UNKNOWN_KEY");static const auto handles=[] {std::vector<Definition> v;v.reserve(17);for(std::size_t i=0;i<17;++i)v.push_back(Definition(i));return v;}();return handles[found->second];
}
const char* closureSha256() {return compiled::closureSha;}
} // namespace fathom::tasks::piecewise_contacts
