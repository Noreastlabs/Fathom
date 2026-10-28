#include "tasks/HarmonicContactFamily.hpp"
#include "tasks/ManualProcedureDomainReports.hpp"
#include "content/Canonical.hpp"
#include "GeneratedHarmonicContactFamilyData.hpp"
#include <map>
#include <set>
#include <stdexcept>

namespace fathom::tasks::harmonic_contacts {
namespace {
using J=json::Value;
void need(bool value,const char* why){if(!value)throw std::invalid_argument(why);}
const J& at(const J& value,const char* key){need(value.isObject()&&value.find(key),"HARMONIC_REQUIRED_FIELD");return *value.find(key);}
int number(const J& value,int low=0,int high=100000){std::int64_t n{};need(value.integer(n)&&n>=low&&n<=high,"HARMONIC_INTEGER");return static_cast<int>(n);}
Rational rational(const J& value){need(value.isArray()&&value.array().size()==2,"HARMONIC_RATIONAL");return Rational(number(value.array()[0]),number(value.array()[1],1));}
bool hex(const J& value){return value.isString()&&value.string().size()==64&&value.string().find_first_not_of("0123456789abcdef")==std::string::npos;}
struct Table {
    std::vector<J> rows;J contexts=json::parse(compiled::contextsJson);
    std::vector<std::string> keys;std::map<std::string,std::size_t> index;
    Table(){
        need(compiled::rows.size()==118&&contexts.isObject()&&contexts.object().size()==3,"HARMONIC_CLOSED118_CONTEXTS");
        std::set<std::string> identities;std::size_t contacts=0,unknownFingers=0,variants=0,timed=0;
        for(const auto& input:compiled::rows){
            auto row=json::parse(input.json);const auto hash=at(row,"compiled_definition_sha256");auto body=row;body.object().erase("compiled_definition_sha256");
            need(hex(hash)&&hash==J(content::sha256(json::stringify(body)))&&hex(at(row,"source_record_canonical_sha256"))&&at(row,"schema")==J("fathom.compiled-harmonic-contact-definition.1"),"HARMONIC_COMPILED_ROW_HASH_SCHEMA");
            need(hex(at(row,"contract_sha256"))&&at(row,"contract_sha256")==J(content::sha256(json::stringify(at(row,"source_contracts")))),"HARMONIC_RETAINED_SOURCE_CONTRACT_HASH");
            need(at(row,"source_key")==J(input.key)&&index.emplace(input.key,rows.size()).second&&identities.insert(at(row,"source_identity").string()).second,"HARMONIC_CLOSED_KEY_IDENTITY");
            const int level=number(at(row,"level"));need(level==40||level==46||level==47,"HARMONIC_EXACT_LEVEL");const auto& context=at(contexts,std::to_string(level).c_str());
            need(at(row,"context_ref")==at(context,"context_ref")&&at(at(context,"source_context"),"level")==at(row,"level"),"HARMONIC_CONTEXT_JOIN");
            const auto& program=at(row,"program");need(at(program,"native_music_model")==J(false)&&at(program,"source_clock").null()&&at(program,"source_acoustic_gates").null()&&at(program,"inherits_physical_tempo_rule")==J(false)&&at(program,"inherits_physical_frame_or_pick_debt")==J(false),"HARMONIC_NO_PHYSICAL_POLICY_FALLBACK");
            const auto& atoms=at(row,"source_atoms").array();need(!atoms.empty(),"HARMONIC_SOURCE_CONTACTS");Rational next;bool metric=!at(atoms[0],"onset_q").null();
            for(std::size_t n=0;n<atoms.size();++n){const auto& atom=atoms[n];
                need(number(at(atom,"ordinal"),1)==static_cast<int>(n+1)&&number(at(atom,"string_low_to_high"),1,6)>=1&&number(at(atom,"fret"),0,127)>=0&&number(at(atom,"midi"),0,127)>=0&&at(atom,"pick_attack")==J(true)&&at(atom,"attack")==J("picked")&&at(atom,"acoustic_gate_q").null(),"HARMONIC_TYPED_PICKED_SOURCE_ATOM");
                static const char* labels[]{"E","A","D","G","B","e"};need(at(atom,"string_label")==J(labels[number(at(atom,"string_low_to_high"),1,6)-1]),"HARMONIC_SOURCE_STRING_CONVENTION");
                if(at(atom,"finger").null())++unknownFingers;else (void)number(at(atom,"finger"),1,4);
                need(number(at(atom,"source_line"),1)>0&&number(at(atom,"source_column_1based"),1)>0,"HARMONIC_SOURCE_LOCATOR");
                if(metric){const auto on=rational(at(atom,"onset_q")),duration=rational(at(atom,"duration_q"));need(on==next&&Rational(0)<duration,"HARMONIC_SAVED_METRIC_ORDER");next=on+duration;++timed;}
                else need(at(atom,"onset_q").null()&&at(atom,"duration_q").null(),"HARMONIC_UNKNOWN_SOURCE_METRIC");
            }
            const auto& timing=at(row,"timing_authority");need(at(timing,"fixed_bpm").null()&&at(timing,"ascii_spacing_is_duration")==J(false),"HARMONIC_NO_CLOCK_OR_ASCII_DURATION");
            if(metric)need(at(row,"source_module")==J("J")&&level==47&&atoms.size()==48&&rational(at(timing,"end_q"))==next,"HARMONIC_ONLY_ORIGINAL_QUARTER_MODEL");else need(at(timing,"end_q").null(),"HARMONIC_NO_INVENTED_METRIC_END");
            const auto& contract=at(row,"source_contracts");const auto* picks=contract.find("variants");const auto& starts=at(program,"saved_pick_starts").array();
            need(starts.size()==(picks?2U:0U)&&at(program,"requires_both_saved_starts")==J(picks!=nullptr),"HARMONIC_SAVED_VARIANT_SCOPE");
            if(picks){need(picks->isArray()&&picks->array().size()==2,"HARMONIC_TWO_ORIGINAL_STARTS");for(std::size_t s=0;s<2;++s){const auto& v=picks->array()[s];need(starts[s]==J(s?"U":"D")&&at(v,"pick_start")==starts[s],"HARMONIC_PICK_START_ORDER");const auto& ord=at(v,"contact_ordinals").array();const auto& strokes=at(v,"strokes_by_contact").array();need(ord.size()==atoms.size()&&strokes.size()==atoms.size(),"HARMONIC_PICK_CONTACT_COUNT");for(std::size_t n=0;n<atoms.size();++n)need(number(ord[n],1)==static_cast<int>(n+1)&&strokes[n]==J((n+s)%2?"U":"D"),"HARMONIC_ORIGINAL_PICK_CONTINUITY");}variants+=2;}
            const auto& phases=at(program,"report_phases").array();need(!phases.empty(),"HARMONIC_MATERIAL_PHASES");int last=0;
            for(const auto& phase:phases){const int after=number(at(phase,"after_source_ordinal"),1,static_cast<int>(atoms.size()));need(after>=last&&at(phase,"source_refs").isArray()&&!at(phase,"source_refs").array().empty()&&at(at(phase,"report_schema"),"additionalProperties")==J(false),"HARMONIC_SOURCE_BOUND_PHASE_ORDER");last=after;}
            need(last==static_cast<int>(atoms.size()),"HARMONIC_COMPLETE_SOURCE_EXTENT_PHASE");contacts+=atoms.size();keys.emplace_back(input.key);rows.push_back(std::move(row));
        }
        need(contacts==1510&&unknownFingers==1070&&variants==70&&timed==48,"HARMONIC_EXACT1510_UNKNOWN_VARIANT_METRIC_TOTALS");
    }
};
const Table& table(){static const Table value;return value;}
const J& row(std::size_t index){need(index<table().rows.size(),"HARMONIC_CLOSED_INDEX");return table().rows[index];}
const char* string(const J& value,const char* key){return at(value,key).string().c_str();}
bool spanEqual(const std::optional<ManualSpan>& a,const std::optional<ManualSpan>& b){return bool(a)==bool(b)&&(!a||(a->onset==b->onset&&a->duration==b->duration));}
}
const char* Definition::sourceKey()const{return string(row(index_),"source_key");}
const char* Definition::sourceIdentity()const{return string(row(index_),"source_identity");}
const char* Definition::sourceRecordSha256()const{return string(row(index_),"source_record_canonical_sha256");}
const char* Definition::packetPath()const{return string(at(row(index_),"payload_ref"),"path");}
const char* Definition::packetSha256()const{return string(at(row(index_),"payload_ref"),"sha256");}
int Definition::packetLine()const{return number(at(at(row(index_),"payload_ref"),"jsonl_line"),1);}
int Definition::level()const{return number(at(row(index_),"level"));}
std::size_t Definition::contactCount()const{return at(row(index_),"source_atoms").array().size();}
std::vector<PickVariant> Definition::savedPickVariants()const{return at(row(index_),"source_contracts").find("variants")?std::vector<PickVariant>{PickVariant::Down,PickVariant::Up}:std::vector<PickVariant>{};}
std::optional<Rational> Definition::selectedMetricEnd()const{const auto& end=at(at(row(index_),"timing_authority"),"end_q");return end.null()?std::nullopt:std::optional<Rational>{rational(end)};}
Cue Definition::contact(std::size_t ordinal,PickVariant start)const{
    need(ordinal>0&&ordinal<=contactCount(),"HARMONIC_EXACT_ORDINAL");const auto& atom=at(row(index_),"source_atoms").array()[ordinal-1];const auto* variants=at(row(index_),"source_contracts").find("variants");std::optional<std::string> pick;
    if(variants){need(start==PickVariant::Down||start==PickVariant::Up,"HARMONIC_SAVED_START_REQUIRED");pick=at(variants->array()[start==PickVariant::Down?0:1],"strokes_by_contact").array()[ordinal-1].string();}else need(start==PickVariant::Unspecified,"HARMONIC_UNSAVED_START_REFUSED");
    std::optional<ManualSpan> span;if(!at(atom,"onset_q").null())span=ManualSpan{rational(at(atom,"onset_q")),rational(at(atom,"duration_q"))};std::optional<int> finger;if(!at(atom,"finger").null())finger=number(at(atom,"finger"),1,4);
    return {sourceKey(),sourceIdentity(),sourceRecordSha256(),ordinal,number(at(atom,"string_low_to_high"),1,6),number(at(atom,"fret")),number(at(atom,"midi"),0,127),finger,at(atom,"string_label").string(),at(atom,"note_spelling").string(),json::stringify(at(atom,"annotations")),at(atom,"attack_authority").string(),pick,span,std::nullopt,number(at(atom,"block_index")),number(at(atom,"grid_column")),number(at(atom,"source_line"),1),number(at(atom,"source_column_1based"),1)};
}
void Definition::requireSourceParity(const Cue& actual,PickVariant start)const{
    const auto expected=contact(actual.ordinal,start);need(actual.sourceKey==expected.sourceKey&&actual.sourceIdentity==expected.sourceIdentity&&actual.sourceRecordSha256==expected.sourceRecordSha256&&actual.ordinal==expected.ordinal&&actual.stringLowToHigh==expected.stringLowToHigh&&actual.fret==expected.fret&&actual.midi==expected.midi&&actual.finger==expected.finger&&actual.stringLabel==expected.stringLabel&&actual.spelling==expected.spelling&&actual.pick==expected.pick&&actual.annotationsJson==expected.annotationsJson&&actual.attackAuthority==expected.attackAuthority&&spanEqual(actual.sourceMetricSpan,expected.sourceMetricSpan)&&!actual.acousticSoundingSpan&&actual.blockIndex==expected.blockIndex&&actual.gridColumn==expected.gridColumn&&actual.sourceLine==expected.sourceLine&&actual.sourceColumn1Based==expected.sourceColumn1Based,"HARMONIC_EXACT_SOURCE_PARITY");
}
std::string Definition::trustedMetadataJson()const{return json::stringify(row(index_));}
std::string Definition::trustedContextJson()const{return json::stringify(at(table().contexts,std::to_string(level()).c_str()));}
std::string Definition::sourceProgramJson()const{return json::stringify(at(row(index_),"program"));}
std::string Definition::sourceAtomsJson()const{return json::stringify(at(row(index_),"source_atoms"));}
bool Definition::reportPhaseResolved(std::size_t index,const J& report)const{const auto& phases=at(at(row(index_),"program"),"report_phases").array();need(index<phases.size(),"HARMONIC_EXACT_PHASE_INDEX");return phaseReportResolved(phases[index],report);}
const std::vector<std::string>& keys(){return table().keys;}
const Definition& definition(const std::string& key){const auto found=table().index.find(key);need(found!=table().index.end(),"HARMONIC_UNKNOWN_SOURCE_KEY");static const auto handles=[](){std::vector<Definition> out;out.reserve(118);for(std::size_t n=0;n<118;++n)out.push_back(Definition(n));return out;}();return handles[found->second];}
const char* closureSha256(){return compiled::closureSha;}
bool phaseReportResolved(const J& phase,const J& report){
    const auto& schema=at(phase,"report_schema");const auto& properties=at(schema,"properties").object();const auto& required=at(schema,"required").array();need(report.isObject()&&report.object().size()==properties.size()&&at(schema,"additionalProperties")==J(false)&&required.size()==properties.size(),"HARMONIC_CLOSED_REPORT_FIELDS");bool resolved=true;
    for(const auto& name:required){need(name.isString()&&properties.count(name.string()),"HARMONIC_REQUIRED_REPORT_SCHEMA");(void)at(report,name.string().c_str());}
    for(const auto& field:properties){const auto& value=at(report,field.first.c_str());const auto& shape=field.second;
        if(const auto* values=shape.find("enum")){need(values->isArray(),"HARMONIC_REPORT_ENUM_SCHEMA");bool allowed=false;for(const auto& allowedValue:values->array())allowed=allowed||value==allowedValue;need(allowed,"HARMONIC_REPORT_ENUM_VALUE");resolved=resolved&&value==J("reported_met");}
        else if(shape.find("minimum")){if(value.null()){resolved=false;continue;}const int n=number(value);const int minimum=number(at(shape,"minimum")),maximum=number(at(shape,"maximum"));need(n<=maximum,"HARMONIC_REPORT_COUNT_BOUND");resolved=resolved&&n>=minimum;}
        else {need(field.first=="evidence","HARMONIC_REPORT_TEXT_FIELD");need(value.null()||value.isString(),"HARMONIC_REPORT_EVIDENCE_TYPE");need(value.null()||manual_procedure_graph_support::utf8TextLength(value.string())<=4096,"HARMONIC_RAW_EVIDENCE_BOUND");resolved=(!value.null()&&manual_procedure_graph_support::nonemptyTrimmedText(value,1,4096))&&resolved;}
    }
    for(const auto& guard:at(phase,"guards").array()) if(at(guard,"kind")==J("minimum")) {
        const auto& value=at(report,at(guard,"field").string().c_str());
        resolved=resolved&&!value.null()&&number(value)>=number(at(guard,"value"));
    }
    return resolved;
}
} // namespace fathom::tasks::harmonic_contacts
