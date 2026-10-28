#include "content/CleanRuntimeEnvelope.hpp"
#include "content/Canonical.hpp"
#include <juce_cryptography/juce_cryptography.h>
#if JUCE_MAC
#include <CommonCrypto/CommonDigest.h>
#endif
#include <algorithm>
#include <array>
#include <fstream>
#include <functional>
#include <iomanip>
#include <limits>
#include <numeric>
#include <set>
#include <sstream>
#include <tuple>

namespace fathom::content {
using J=json::Value;
std::string sha256(const std::string& bytes) {
#if JUCE_MAC
    // The same SHA256 identity, using the existing platform digest on macOS.
    // Chunk lengths fit CC_LONG even when the complete string does not.
    CC_SHA256_CTX context{};
    if(CC_SHA256_Init(&context)!=1)throw std::runtime_error("SHA256 initialization failed");
    constexpr std::size_t chunk=1024*1024;
    static_assert(chunk<=std::numeric_limits<CC_LONG>::max());
    for(std::size_t at=0;at<bytes.size();){
        const auto length=std::min(bytes.size()-at,chunk);
        if(CC_SHA256_Update(&context,bytes.data()+at,static_cast<CC_LONG>(length))!=1)
            throw std::runtime_error("SHA256 update failed");
        at+=length;
    }
    std::array<unsigned char,CC_SHA256_DIGEST_LENGTH> digest{};
    if(CC_SHA256_Final(digest.data(),&context)!=1)throw std::runtime_error("SHA256 finalization failed");
    constexpr char hex[]="0123456789abcdef";
    std::string result;result.reserve(2*digest.size());
    for(const auto value:digest){result+=hex[value>>4];result+=hex[value&15];}
    return result;
#else
    return juce::SHA256(bytes.data(),bytes.size()).toHexString().toStdString();
#endif
}
std::string readBounded(const std::filesystem::path& path,std::size_t limit,
    const CancellationCheck& canceled) {
    checkLoadCanceled(canceled);
    std::error_code ec;
    if(!std::filesystem::is_regular_file(path,ec)||ec) throw std::runtime_error("Input is not an accessible regular file: " + path.string());
    std::ifstream in(path,std::ios::binary);
    if(!in) throw std::runtime_error("Cannot open " + path.string());
    std::string out; char block[65536];
    while(in) { checkLoadCanceled(canceled);in.read(block,sizeof(block)); const auto n=static_cast<std::size_t>(in.gcount());
        if(n>limit-out.size()) throw std::runtime_error("Read exceeds byte limit: " + path.string());
        out.append(block,n);
    }
    if(!in.eof()) throw std::runtime_error("Read failed: " + path.string());
    checkLoadCanceled(canceled);
    return out;
}
namespace {
struct Invalid : std::runtime_error {
    std::string code,path;
    Invalid(std::string c,std::string p,std::string text) : std::runtime_error(std::move(text)),code(std::move(c)),path(std::move(p)) {}
};
[[noreturn]] void bad(const std::string& code,const std::string& path,const std::string& text) { throw Invalid(code,path,text); }
const J& at(const J& j,const std::string& key) { return j.object().at(key); }
void shape(const J& j,const std::string& path,std::initializer_list<const char*> required,std::initializer_list<const char*> optional={}) {
    if(!j.isObject()) bad("TYPE_OBJECT",path,"Expected object");
    std::set<std::string> keys;
    for(auto k:required) { keys.insert(k); if(!j.find(k)) bad("REQUIRED_FIELD",path+"/"+k,"Required field is missing"); }
    for(auto k:optional) keys.insert(k);
    for(const auto& kv:j.object()) if(!keys.count(kv.first)) bad("UNKNOWN_FIELD",path+"/"+kv.first,"Field is unsupported in this schema; use an explicitly reviewed schema revision");
}
const std::string& text(const J& j,const std::string& p,bool empty=false) {
    if(!j.isString()) bad("TYPE_STRING",p,"Expected string");
    if(!empty&&j.string().empty()) bad("EMPTY_STRING",p,"Expected nonempty string");
    return j.string();
}
std::int64_t integer(const J& j,const std::string& p,std::int64_t low,std::int64_t high) {
    std::int64_t n=0;
    if(!j.integer(n)) bad("TYPE_INTEGER",p,"Expected exact signed 64-bit integer token");
    if(n<low||n>high) bad("INTEGER_RANGE",p,"Integer is outside supported range");
    return n;
}
void boolean(const J& j,const std::string& p) { if(!j.isBool()) bad("TYPE_BOOLEAN",p,"Expected boolean"); }
void falseOnly(const J& j,const std::string& p,const char* code) { boolean(j,p); if(j.boolean()) bad(code,p,"Proposal validation supplies no runtime admission, media or automatic feature"); }
const J::Array& array(const J& j,const std::string& p,std::size_t max=1000000) {
    if(!j.isArray()) bad("TYPE_ARRAY",p,"Expected array");
    if(j.array().size()>max) bad("COLLECTION_LIMIT",p,"Collection exceeds declared limit");
    return j.array();
}
void strings(const J& j,const std::string& p,bool unique=false) {
    std::set<std::string> seen; std::size_t i=0;
    for(const auto& v:array(j,p)) { const auto s=text(v,p+"/"+std::to_string(i++)); if(unique&&!seen.insert(s).second) bad("DUPLICATE_REFERENCE",p,"Duplicate reference"); }
}
void oneOf(const J& j,const std::string& p,std::initializer_list<const char*> values) {
    const auto& s=text(j,p); for(auto v:values) if(s==v) return;
    bad("UNSUPPORTED_VALUE",p,"Unsupported discriminator or configuration");
}
void nullableString(const J& j,const std::string& p) { if(!j.null()) text(j,p); }
std::optional<Rational> rational(const J& j,const std::string& p) {
    if(j.null()) return {};
    if(array(j,p,2).size()!=2) bad("RATIONAL_SHAPE",p,"Expected [numerator,denominator]");
    auto n=integer(j.array()[0],p+"/0",0,std::numeric_limits<std::int64_t>::max());
    auto d=integer(j.array()[1],p+"/1",1,std::numeric_limits<std::int64_t>::max());
    if(std::gcd(n,d)!=1) bad("RATIONAL_REDUCED",p,"Quarter value must be reduced");
    return Rational(n,d);
}
void hashText(const J& j,const std::string& p) {
    const auto& s=text(j,p);
    if(s.size()!=64||s.find_first_not_of("0123456789abcdef")!=std::string::npos) bad("SHA256_FORMAT",p,"Expected lowercase SHA-256 hex");
}
void tone(const J& j,const std::string& p,bool top) {
    if(top) shape(j,p,{"kind","string","fret","midi","spelling","degree_contexts","finger","onset_q","duration_q","attack","tie_from","event_id"},{"pick","bend"});
    else shape(j,p,{"kind","string","fret","midi","spelling","degree_contexts","finger","onset_q","duration_q","attack","tie_from"},{"bend"});
    oneOf(at(j,"kind"),p+"/kind",{"note"});
    integer(at(j,"string"),p+"/string",1,128); integer(at(j,"fret"),p+"/fret",0,127); integer(at(j,"midi"),p+"/midi",0,127);
    nullableString(at(j,"spelling"),p+"/spelling");
    const auto& f=at(j,"finger");
    if(!f.null()) { if(f.isString()) oneOf(f,p+"/finger",{"O"}); else integer(f,p+"/finger",1,4); }
    rational(at(j,"onset_q"),p+"/onset_q"); rational(at(j,"duration_q"),p+"/duration_q");
    oneOf(at(j,"attack"),p+"/attack",{"picked","hammer_on","pull_off","slide_arrival","bend","held","blue_third_shade","harmonic","vibrato"});
    if(top) if(const auto pick=j.find("pick")) {
        oneOf(*pick,p+"/pick",{"D","U"});
        if(at(j,"attack").string()!="picked" || !at(j,"tie_from").null())
            bad("PICK_ATTACK",p+"/pick","A pitched note stroke requires its own picked attack without a held link");
    }
    nullableString(at(j,"tie_from"),p+"/tie_from");
    if(const auto b=j.find("bend")) {
        if(at(j,"attack").string()!="bend") bad("BEND_ATTACK",p+"/bend","Only Bend may carry a contour");
        shape(*b,p+"/bend",{"target_semitones","knots"},{"mode","initial_offset_semitones"});
        const auto target=rational(at(*b,"target_semitones"),p+"/bend/target_semitones");
        if(!target || *target==Rational{}) bad("BEND_TARGET",p+"/bend/target_semitones","Positive bend interval required");
        const auto mode=b->find("mode");
        if(mode) oneOf(*mode,p+"/bend/mode",{"rise_hold_release","prebent_release"});
        const auto initial=b->find("initial_offset_semitones");
        if(mode && mode->string()=="prebent_release") {
            if(!initial) bad("BEND_INITIAL_REQUIRED",p+"/bend/initial_offset_semitones","Pre-bent release needs an explicit silent initial offset");
            if(!rational(*initial,p+"/bend/initial_offset_semitones"))
                bad("BEND_INITIAL_REQUIRED",p+"/bend/initial_offset_semitones","Pre-bent release needs a non-null initial offset");
        } else if(initial) bad("BEND_INITIAL_MODE",p+"/bend/initial_offset_semitones","Initial offset requires explicit pre-bent release mode");
        for(const auto& knot:array(at(*b,"knots"),p+"/bend/knots",64)) {
            shape(knot,p+"/bend/knots",{"q","offset_semitones"});
            if(!rational(at(knot,"q"),p+"/bend/knots/q") || !rational(at(knot,"offset_semitones"),p+"/bend/knots/offset_semitones"))
                bad("BEND_KNOT",p+"/bend/knots","Bend knot values must be explicit");
        }
    }
    const auto& degrees=at(j,"degree_contexts");
    if(!degrees.isObject()) bad("TYPE_OBJECT",p+"/degree_contexts","Expected named degree contexts");
    for(const auto& kv:degrees.object()) {
        if(kv.first.empty()) bad("EMPTY_STRING",p+"/degree_contexts","Empty degree context");
        const auto q=p+"/degree_contexts/"+kv.first; shape(kv.second,q,{"source_label","ordinal","alteration"});
        text(at(kv.second,"source_label"),q+"/source_label"); integer(at(kv.second,"ordinal"),q+"/ordinal",1,128); integer(at(kv.second,"alteration"),q+"/alteration",-2,2);
    }
}
void eventShape(const J& e,const std::string& p) {
    if(!e.isObject()||!e.find("kind")) bad("EVENT_KIND",p,"Event kind is required");
    const auto k=text(at(e,"kind"),p+"/kind");
    if(k=="note") tone(e,p,true);
    else if(k=="rest") {
        shape(e,p,{"kind","onset_q","duration_q","event_id"},{"scope_strings"});
        if(const auto scope=e.find("scope_strings")) {
            std::set<std::int64_t> seen;
            for(const auto& value:array(*scope,p+"/scope_strings",128)) {
                const auto string=integer(value,p+"/scope_strings",1,128);
                if(!seen.insert(string).second) bad("REST_SCOPE_DUPLICATE",p+"/scope_strings","Rest scope contains duplicate strings");
            }
            if(seen.empty()) bad("REST_SCOPE_EMPTY",p+"/scope_strings","Explicit rest scope cannot be empty");
        }
    }
    else if(k=="chord") {
        shape(e,p,{"kind","symbol","onset_q","duration_q","members","attack","event_id"},{"pick"}); text(at(e,"symbol"),p+"/symbol");
        oneOf(at(e,"attack"),p+"/attack",{"simultaneous_example"});
        std::size_t i=0; for(const auto& m:array(at(e,"members"),p+"/members",128)) tone(m,p+"/members/"+std::to_string(i++),false);
        if(const auto pick=e.find("pick")) {
            oneOf(*pick,p+"/pick",{"D","U"});
            if(at(e,"members").array().empty())
                bad("PICK_ATTACK",p+"/pick","A chord stroke requires a voiced picked chord");
            for(const auto& m:at(e,"members").array())
                if(at(m,"attack").string()!="picked" || !at(m,"tie_from").null())
                    bad("PICK_ATTACK",p+"/pick","A chord stroke requires every member to be picked without a held link");
        }
    } else if(k=="contact") {
        shape(e,p,{"kind","contact","onset_q","duration_q","pick","pitch_binding","event_id"},{"scope_strings"});
        oneOf(at(e,"contact"),p+"/contact",{"pitched","muted","air","release","sustain"}); oneOf(at(e,"pick"),p+"/pick",{"D","U"});
        const bool muted=at(e,"contact").string()=="muted";
        if(muted && !e.find("scope_strings")) bad("MUTED_SCOPE_REQUIRED",p+"/scope_strings","Muted contact needs explicit string scope");
        if(!muted && e.find("scope_strings")) bad("CONTACT_SCOPE_KIND",p+"/scope_strings","Only muted contacts use this scope contract");
        if(muted) {
            const auto& values=array(at(e,"scope_strings"),p+"/scope_strings",6);
            if(values.empty()) bad("MUTED_SCOPE_EMPTY",p+"/scope_strings","Muted contact scope cannot be empty");
            std::set<std::int64_t> seen;
            for(const auto& value:values) {
                const auto string=integer(value,p+"/scope_strings",1,6);
                if(!seen.insert(string).second) bad("MUTED_SCOPE_DUPLICATE",p+"/scope_strings","Muted contact scope must be unique");
            }
        }
        if(!at(e,"pitch_binding").null()) bad("UNSUPPORTED_BINDING",p+"/pitch_binding","Proposal schema leaves contact pitch/gate binding unresolved; requires explicit converted schema");
    } else bad("EVENT_KIND",p+"/kind","Unsupported event kind");
    text(at(e,"event_id"),p+"/event_id"); rational(at(e,"onset_q"),p+"/onset_q"); rational(at(e,"duration_q"),p+"/duration_q");
}
void stringMap(const J& j,const std::string& p) {
    if(!j.isObject()) bad("TYPE_OBJECT",p,"Expected string map");
    for(const auto& kv:j.object()) text(kv.second,p+"/"+kv.first);
}
void contextShape(const J& c,const std::string& p) {
    shape(c,p,{}, {"local_code","route","pick_start","position","tuning_open_midi","capo","mode","pick_start_variants","authored_progression_ref","pick_continues_at_turn","source_tempo_rules_ref","degree_encoding_examples","reference_tonal_centers","source_count_classes","technique_legend","held_response_example","bend_contract","color_context","open_finger_token","muted_string_token","chord_voicings_are_alternatives","authored_contacts","symbol_semantics","freeplay_default_selected","table","fixed_melody","task_obligations","maximum_legacy_level","failed_domain_return_refs","no_automatic_mastery"});
    for(const auto& kv:c.object()) {
        const auto& k=kv.first; const auto& v=kv.second; const auto q=p+"/"+k;
        if(k=="tuning_open_midi") { for(const auto& n:array(v,q,128)) integer(n,q,0,127); if(v.array().empty()) bad("INSTRUMENT_EMPTY",q,"Tuning cannot be empty"); }
        else if(k=="capo") integer(v,q,0,127);
        else if(k=="authored_contacts"||k=="maximum_legacy_level") integer(v,q,1,1000000);
        else if(k=="pick_continues_at_turn"||k=="chord_voicings_are_alternatives"||k=="fixed_melody"||k=="no_automatic_mastery") boolean(v,q);
        else if(k=="freeplay_default_selected") falseOnly(v,q,"SOURCE_DEFAULT_NOT_SELECTED");
        else if(k=="reference_tonal_centers"||k=="task_obligations") strings(v,q);
        else if(k=="pick_start_variants") { for(const auto& a:array(v,q)) oneOf(a,q,{"D","U"}); }
        else if(k=="degree_encoding_examples") {
            for(const auto& a:array(v,q)) { shape(a,q,{"source","simple","octaves_above"}); text(at(a,"source"),q+"/source"); integer(at(a,"simple"),q+"/simple",1,7); integer(at(a,"octaves_above"),q+"/octaves_above",0,20); }
        } else if(k=="source_count_classes") { shape(v,q,{"full_written_sounding_tones","full_written_pick_attacks"}); for(const auto& a:v.object()) integer(a.second,q+"/"+a.first,0,10000000); }
        else if(k=="technique_legend"||k=="symbol_semantics") stringMap(v,q);
        else if(k=="held_response_example") { shape(v,q,{"source_ref","source_slots","rule","duration_q"}); text(at(v,"source_ref"),q); strings(at(v,"source_slots"),q); text(at(v,"rule"),q); rational(at(v,"duration_q"),q+"/duration_q"); }
        else if(k=="bend_contract") { shape(v,q,{"base_pitch","target_interval","contour"}); stringMap(v,q); }
        else if(k=="table") {
            std::set<std::int64_t> bars;
            for(const auto& a:array(v,q)) {
                shape(a,q,{"bar","chord_symbol","top_pitch_class","bass_inversion"}); auto bar=integer(at(a,"bar"),q+"/bar",1,1000000);
                if(!bars.insert(bar).second) bad("TABLE_DUPLICATE_BAR",q,"Duplicate table bar");
                text(at(a,"chord_symbol"),q+"/chord_symbol"); const auto s=text(at(a,"top_pitch_class"),q+"/top_pitch_class");
                try { music::pitchClass(s); } catch(const std::exception&) { bad("PITCH_CLASS",q+"/top_pitch_class","Invalid pitch spelling"); }
                if(!at(a,"bass_inversion").null()) bad("UNAUTHORED_BASS",q+"/bass_inversion","Proposal task table supplies no bass inversion");
            }
        } else text(v,q);
    }
    if((c.find("capo")!=nullptr)!=(c.find("tuning_open_midi")!=nullptr)) bad("INSTRUMENT_CONTEXT",p,"Tuning and capo must be supplied together");
}
void timingShape(const J& t,const std::string& p) {
    shape(t,p,{"status","unit","basis"},{"variants","meter","phrases","other_source_requirements"});
    oneOf(at(t,"status"),p+"/status",{"unresolved","source_defined","not_applicable"}); oneOf(at(t,"unit"),p+"/unit",{"quarter"}); text(at(t,"basis"),p+"/basis");
    if(const auto m=t.find("meter");m&&!m->null()) { if(array(*m,p+"/meter",2).size()!=2) bad("METER_SHAPE",p+"/meter","Expected meter numerator/denominator"); integer(m->array()[0],p+"/meter/0",1,64); const auto d=integer(m->array()[1],p+"/meter/1",1,64); if((d&(d-1))!=0) bad("METER_DENOMINATOR",p+"/meter/1","Expected power-of-two denominator"); }
    if(const auto v=t.find("variants")) {
        std::set<std::string> ids;
        for(const auto& a:array(*v,p+"/variants")) {
            if(!a.isObject()) bad("TYPE_OBJECT",p+"/variants","Expected timing variant");
            if(a.find("post_cell_rest_q")) { shape(a,p,{"id","post_cell_rest_q"}); rational(at(a,"post_cell_rest_q"),p+"/post_cell_rest_q"); }
            else { shape(a,p,{"id","notes_per_beat","marking_factor"}); integer(at(a,"notes_per_beat"),p+"/notes_per_beat",1,64); rational(at(a,"marking_factor"),p+"/marking_factor"); }
            if(!ids.insert(text(at(a,"id"),p+"/id")).second) bad("DUPLICATE_ID",p+"/variants","Duplicate variant ID");
        }
    }
    if(const auto phrases=t.find("phrases")) for(const auto& a:array(*phrases,p+"/phrases")) {
        shape(a,p,{"ratio","common_cycle_q","phrase_q","cycles","resolution_q"}); if(array(at(a,"ratio"),p+"/ratio",2).size()!=2) bad("RATIO_SHAPE",p,"Expected two layer counts");
        for(const auto& n:at(a,"ratio").array()) integer(n,p+"/ratio",1,64);
        const auto common=rational(at(a,"common_cycle_q"),p+"/common_cycle_q");
        const auto phrase=rational(at(a,"phrase_q"),p+"/phrase_q");
        const auto resolution=rational(at(a,"resolution_q"),p+"/resolution_q");
        const auto cycles=integer(at(a,"cycles"),p+"/cycles",1,1000000);
        if(!common||!phrase||*common==Rational{}||*phrase==Rational{}) bad("PHRASE_ZERO_SPAN",p+"/phrases","Common cycle and phrase must have explicit positive spans");
        if(common->numerator()>std::numeric_limits<std::int64_t>::max()/cycles) bad("PHRASE_ARITHMETIC_RANGE",p+"/phrases","Cycle span arithmetic exceeds exact representation");
        const Rational span(common->numerator()*cycles,common->denominator());
        if(*phrase<span) bad("PHRASE_CYCLE_BOUNDS",p+"/phrases","Declared complete cycles exceed the phrase span");
        if(resolution&&(!(*resolution==span)||!(*resolution<*phrase))) bad("PHRASE_RESOLUTION",p+"/resolution_q","Declared return follows the complete cycles and lies within the phrase; the remaining resolution beat is preserved");
    }
    if(const auto o=t.find("other_source_requirements")) strings(*o,p+"/other_source_requirements");
}
void repeatability(const J& j,const std::string& p,bool nested=false) {
    if(!j.isObject()||!j.find("kind")) bad("REPEATABILITY_KIND",p,"Repeatability requires a kind");
    const auto k=text(at(j,"kind"),p+"/kind");
    if(k=="two_separate_days") shape(j,p,{"kind"});
    else if(k=="two_unfamiliar_excerpts") { shape(j,p,{"kind","same_excerpt_twice_counts"}); falseOnly(at(j,"same_excerpt_twice_counts"),p+"/same_excerpt_twice_counts","UNFAMILIARITY_REQUIRED"); }
    else if(k=="one_passing_performance_independent_reviewer") { shape(j,p,{"kind","minimum_reviewer_total"}); integer(at(j,"minimum_reviewer_total"),p+"/minimum_reviewer_total",1,1000); }
    else if(k=="any_of"&&!nested) {
        shape(j,p,{"kind","alternatives","alternative_affects"}); oneOf(at(j,"alternative_affects"),p+"/alternative_affects",{"repeatability_only"});
        if(array(at(j,"alternatives"),p+"/alternatives",8).size()<2) bad("REPEATABILITY_ALTERNATIVES",p,"Expected at least two alternatives");
        for(const auto& a:at(j,"alternatives").array()) repeatability(a,p+"/alternatives",true);
    } else bad("REPEATABILITY_KIND",p+"/kind","Unsupported repeatability condition");
}
void rubricShape(const J& r,const std::string& p) {
    if(r.null()) return;
    shape(r,p,{"dimensions","minimum_total","maximum_total","protected_nonzero","repeatability","required_obligations_refs","required_obligations","evidence_kind"});
    std::set<std::string> names; std::int64_t total=0;
    for(const auto& d:array(at(r,"dimensions"),p+"/dimensions",128)) {
        shape(d,p,{"name","anchors"}); if(!names.insert(text(at(d,"name"),p+"/name")).second) bad("RUBRIC_DIMENSION_DUPLICATE",p,"Duplicate dimension");
        strings(at(d,"anchors"),p+"/anchors"); if(at(d,"anchors").array().size()<2) bad("RUBRIC_ANCHORS",p,"Dimension needs distinct score anchors"); total+=static_cast<std::int64_t>(at(d,"anchors").array().size()-1);
    }
    const auto max=integer(at(r,"maximum_total"),p+"/maximum_total",1,100000); integer(at(r,"minimum_total"),p+"/minimum_total",1,max);
    if(max!=total) bad("RUBRIC_TOTAL",p+"/maximum_total","Total does not equal dimension anchor scores");
    strings(at(r,"protected_nonzero"),p+"/protected_nonzero",true);
    for(const auto& n:at(r,"protected_nonzero").array()) if(!names.count(n.string())) bad("RUBRIC_PROTECTED",p+"/protected_nonzero","Protected domain is not a dimension");
    repeatability(at(r,"repeatability"),p+"/repeatability"); strings(at(r,"required_obligations_refs"),p+"/required_obligations_refs",true); strings(at(r,"required_obligations"),p+"/required_obligations");
    oneOf(at(r,"evidence_kind"),p+"/evidence_kind",{"explicit_learner_or_reviewer_attestation"});
}
void recordShape(const J& r,const std::string& p,const Limits& limits,bool candidate,bool curriculum) {
    shape(r,p,{"id","workbook_id","module_id","legacy_level","title","kind","content_revision","status","runtime_eligible","source_refs","authored_text_refs","normalization","context","events","timing","rubric","resource_requirements","ambiguities"},{"control_scope","variants","lineage","terminal_q"});
    if(curriculum&&!r.find("lineage")) bad("LINEAGE_REQUIRED",p,"Schema1 requires explicit new or revision lineage");
    if(!curriculum&&r.find("lineage")) bad("UNKNOWN_FIELD",p+"/lineage","Lineage requires schema1");
    if(candidate) { if(!r.find("control_scope")||!r.find("variants")) bad("CANDIDATE_FIELDS",p,"Candidate requires scope and variant definitions"); }
    else if(r.find("control_scope")||r.find("variants")) bad("CANDIDATE_FIELDS",p,"Candidate constructs require the candidate schema");
    for(auto k:{"id","workbook_id","module_id","title"}) text(at(r,k),p+"/"+k);
    integer(at(r,"legacy_level"),p+"/legacy_level",1,105); integer(at(r,"content_revision"),p+"/content_revision",1,std::numeric_limits<int>::max());
    oneOf(at(r,"kind"),p+"/kind",{"notation","instruction","mixed","harmony","rhythm","task"});
    if(text(at(r,"status"),p+"/status")!=(candidate?"converted_candidate":"proposal_example")) bad("SCHEMA_STATUS",p+"/status","Status must match explicit package schema"); falseOnly(at(r,"runtime_eligible"),p+"/runtime_eligible","RUNTIME_NOT_ADMITTED");
    strings(at(r,"source_refs"),p+"/source_refs",true); strings(at(r,"authored_text_refs"),p+"/authored_text_refs",true); strings(at(r,"ambiguities"),p+"/ambiguities");
    for(const auto& n:array(at(r,"normalization"),p+"/normalization")) {
        if(!n.isObject()||!n.find("kind")) bad("NORMALIZATION_KIND",p+"/normalization","Normalization requires labelled kind");
        const auto k=text(at(n,"kind"),p+"/normalization/kind");
        if(k=="accepted_navigation") { shape(n,p,{"kind","basis","value","source_authority"}); stringMap(at(n,"value"),p+"/value"); text(at(n,"source_authority"),p+"/source_authority"); }
        else if(k=="representation_metadata"||k=="accepted_explanation") { shape(n,p,{"kind","basis","text"}); text(at(n,"text"),p+"/text"); }
        else bad("NORMALIZATION_KIND",p+"/normalization/kind","Unsupported normalization kind");
        text(at(n,"basis"),p+"/basis");
    }
    contextShape(at(r,"context"),p+"/context"); timingShape(at(r,"timing"),p+"/timing"); rubricShape(at(r,"rubric"),p+"/rubric");
    if(const auto terminal=r.find("terminal_q")) {const auto endpoint=rational(*terminal,p+"/terminal_q");if(!endpoint || !(Rational{}<*endpoint))bad("TERMINAL_ENDPOINT",p+"/terminal_q","Terminal endpoint must be explicit and positive");}
    std::size_t i=0; for(const auto& e:array(at(r,"events"),p+"/events",limits.events)) eventShape(e,p+"/events/"+std::to_string(i++));
    for(const auto& resource:array(at(r,"resource_requirements"),p+"/resource_requirements")) {
        shape(resource,p,{"kind","purpose","supplied","in_app_import","in_app_recorder","disposition"}); oneOf(at(resource,"kind"),p+"/resource_requirements/kind",{"learner_teacher_offline"});
        text(at(resource,"purpose"),p+"/resource_requirements/purpose"); text(at(resource,"disposition"),p+"/resource_requirements/disposition");
        for(auto key:{"supplied","in_app_import","in_app_recorder"}) falseOnly(at(resource,key),p+"/resource_requirements/"+key,"RESOURCE_UNSUPPLIED");
    }
}
class Validator {
    const Input& input;
    const Limits& limits;
    J package,registry,profile;
    J::Array issues, recordReports, variantReports;
    J allocation, identityBaseline, allocationBaseline, lineageBaseline;
    std::map<std::string,const J*> baselineEntities;
    std::map<std::string,J> predecessorRecords;
    std::map<std::string,std::string> baselineOccurrences, baselineVariants;
    std::map<std::string,std::string> predecessorHashes;
    std::set<std::string> usedVariants;
    std::size_t variantEventTotal=0;
    bool candidate=false,curriculum=false;
    std::map<std::string,J> assets;
    std::map<std::string,J> archivedEvidence;
    std::map<std::string,const J*> entities, expectedEntities, records, expectedRecords;
    std::filesystem::path root;
    std::size_t assetTotal=0,eventTotal=0;
    bool failed=false;
    Result result;
    void checkpoint() const { checkLoadCanceled(input.canceled); }
    void issue(const std::string& code,const std::string& field,const std::string& message,const std::string& record="",const std::string& event="",const std::string& source="",const std::string& severity="error") {
        if(severity=="error") failed=true;
        issues.emplace_back(J::Object{{"severity",severity},{"code",code},{"field",field},{"record",record},{"event",event},{"source",source},{"message",message}});
    }
    template<class F> bool guard(F operation,const std::string& record="",const std::string& source="") {
        try { checkpoint();operation();checkpoint();return true; }
        catch(const LoadCanceled&) { throw; }
        catch(const Invalid& e) { issue(e.code,e.path,e.what(),record,"",source); }
        catch(const std::exception& e) { issue("INPUT_FAILURE","/",e.what(),record,"",source); }
        return false;
    }
    void compare(const J& actual,const J& expected,const std::string& path,const std::string& code,const std::string& record="") {
        checkpoint();
        if(actual==expected) return;
        if(actual.isObject()&&expected.isObject()) {
            for(const auto& kv:expected.object()) {
                const auto a=actual.find(kv.first);
                if(!a) issue(code,path+"/"+kv.first,"Required reference field is absent",record);
                else compare(*a,kv.second,path+"/"+kv.first,code,record);
            }
            for(const auto& kv:actual.object()) if(!expected.find(kv.first)) issue(code,path+"/"+kv.first,"Field is absent from reviewed reference",record);
        } else if(actual.isArray()&&expected.isArray()) {
            if(actual.array().size()!=expected.array().size()) issue(code,path,"Array length differs from required reference",record);
            for(std::size_t i=0;i<std::min(actual.array().size(),expected.array().size());++i) compare(actual.array()[i],expected.array()[i],path+"/"+std::to_string(i),code,record);
        } else issue(code,path,"Value differs from independently bound reference",record);
    }
    static std::set<std::string> keys(const std::map<std::string,const J*>& m) { std::set<std::string>s; for(const auto& kv:m)s.insert(kv.first); return s; }
    static std::set<std::string> objectKeys(const J& j) { std::set<std::string>s; for(const auto& kv:j.object())s.insert(kv.first); return s; }
    void coverage(const std::set<std::string>& actual,const std::set<std::string>& expected,const std::string& p) {
        for(const auto& id:expected) if(!actual.count(id)) issue("COVERAGE_MISSING",p+"/"+id,"Expected stable identity is missing");
        for(const auto& id:actual) if(!expected.count(id)) issue("COVERAGE_UNEXPECTED",p+"/"+id,"Stable identity is outside expected coverage");
    }
    std::filesystem::path sourcePath(const std::string& relative) {
        if(relative.empty()||relative.find('\0')!=std::string::npos||relative.find('\\')!=std::string::npos) bad("SOURCE_PATH",relative,"Invalid relative source path");
        std::filesystem::path p(relative);
        if(p.is_absolute()||p.has_root_name()) bad("SOURCE_PATH",relative,"Absolute source paths are forbidden");
        for(const auto& part:p) if(part==".."||part==".") bad("SOURCE_PATH",relative,"Dot traversal is forbidden");
        std::error_code ec;
        const auto requested=root/p;
        auto withinRoot=[&](const std::filesystem::path& candidate){
            auto a=root.begin(),b=candidate.begin();
            for(;a!=root.end();++a,++b) if(b==candidate.end()||*a!=*b) bad("SOURCE_ESCAPE",relative,"Resolved source escapes the supplied root");
        };
        const auto status=std::filesystem::symlink_status(requested,ec);
        if(ec&&ec!=std::make_error_code(std::errc::no_such_file_or_directory)) bad("SOURCE_READ",relative,"Source path cannot be inspected: "+ec.message());
        const bool missing=status.type()==std::filesystem::file_type::not_found;
        auto selected=requested;
        if(missing) {
            ec.clear(); const auto prospective=std::filesystem::weakly_canonical(requested,ec);
            if(ec) bad("SOURCE_READ",relative,"Source path cannot be inspected: "+ec.message());
            withinRoot(prospective);
            const auto suffix=p.lexically_relative("Results");
            if(relative.rfind("Results/",0)==0&&relative.rfind("Results/primary/",0)!=0&&!suffix.empty()&&suffix!=".")
                selected=root/"Results/primary"/suffix;
        }
        ec.clear(); auto resolved=std::filesystem::canonical(selected,ec);
        if(ec) bad("SOURCE_READ",relative,"Source path cannot be resolved: "+ec.message());
        withinRoot(resolved);
        if(!std::filesystem::is_regular_file(resolved,ec)||ec) bad("SOURCE_READ",relative,"Source is not a regular file");
        return resolved;
    }
    std::string asset(const std::string& relative,const std::string& expectedHash,bool needBytes=false) {
        checkpoint();
        const auto resolved=sourcePath(relative);
        const auto key=resolved.string();
        if(assets.count(key)) {
            if(at(assets.at(key),"sha256").string()!=expectedHash) bad("SOURCE_HASH",relative,"Source hash differs from expected identity");
            if(needBytes) { auto bytes=readBounded(resolved,limits.assetBytes,input.canceled);checkpoint();if(sha256(bytes)!=expectedHash) bad("SOURCE_CHANGED",relative,"Source changed during validation");if(input.installedRuntime)input.installedRuntime->verifyPayload(resolved,bytes);checkpoint();return bytes; }
            return {};
        }
        std::error_code ec; auto size=std::filesystem::file_size(resolved,ec);
        if(ec) bad("SOURCE_READ",relative,"Cannot determine source size");
        if(size>limits.assetBytes) bad("SOURCE_ASSET_LIMIT",relative,"Unique source asset exceeds limit");
        if(size>limits.totalAssetBytes-assetTotal) bad("SOURCE_TOTAL_LIMIT",relative,"Aggregate unique asset bytes exceed limit");
        auto bytes=readBounded(resolved,limits.assetBytes,input.canceled);
        checkpoint();
        if(bytes.size()>limits.totalAssetBytes-assetTotal) bad("SOURCE_TOTAL_LIMIT",relative,"Aggregate unique asset bytes exceed limit");
        if(input.installedRuntime)input.installedRuntime->verifyPayload(resolved,bytes);
        const auto hash=sha256(bytes); assetTotal+=bytes.size();
        checkpoint();
        assets.emplace(key,J::Object{{"path",relative},{"sha256",hash},{"bytes",J::fromInteger(static_cast<std::int64_t>(bytes.size()))}});
        if(hash!=expectedHash) bad("SOURCE_HASH",relative,"Actual source bytes differ from expected SHA-256");
        return needBytes?bytes:std::string{};
    }
    void packageShape(const J& j,const std::string& p,bool allowCatalog=false) {
        if(!j.isObject()||!j.find("schema_version")) bad("REQUIRED_FIELD",p+"/schema_version","Package schema version is required");
        const bool schema1=j.find("schema_version")->isString()&&j.find("schema_version")->string()=="1.0.0-curriculum-candidate";
        if(schema1&&allowCatalog) shape(j,p,{"schema_version","content_version","source_manifest_sha256","source_acceptance","sources","records"},{"workbook_catalog"});
        else shape(j,p,{"schema_version","content_version","source_manifest_sha256","source_acceptance","sources","records"});
        oneOf(at(j,"schema_version"),p+"/schema_version",{"0.1.0-proposal","0.2.0-control-candidate","1.0.0-curriculum-candidate"}); text(at(j,"content_version"),p+"/content_version"); hashText(at(j,"source_manifest_sha256"),p+"/source_manifest_sha256"); text(at(j,"source_acceptance"),p+"/source_acceptance");
        if(!at(j,"sources").isObject()) bad("TYPE_OBJECT",p+"/sources","Expected passage map");
        if(at(j,"sources").object().size()>limits.sources) bad("SOURCE_COUNT_LIMIT",p+"/sources","Too many passages");
        if(array(at(j,"records"),p+"/records",limits.records).empty()) bad("EMPTY_PACKAGE",p+"/records","Empty package cannot pass coverage validation");
    }
    void catalogShape(const J& catalog,const std::string& p) {
        shape(catalog,p,{"catalog_version","entries","inventory_bindings","inventory_map","scope"});
        const auto& version=text(at(catalog,"catalog_version"),p+"/catalog_version");
        const std::string prefix="curriculum-v1-workbook-source-catalog.";
        if(version.compare(0,prefix.size(),prefix)!=0||version.size()<=prefix.size()||
           version.find_first_not_of("0123456789",prefix.size())!=std::string::npos||
           version[prefix.size()]=='0') bad("CATALOG_VERSION",p+"/catalog_version","Expected a positive source-catalog version");
        auto safePath=[&](const J& value,const std::string& where,const std::string& requiredPrefix) {
            const auto& raw=text(value,where);
            if(raw.size()>4096||raw.front()=='/'||raw.back()=='/'||raw.find('\\')!=std::string::npos||
               raw.find('\0')!=std::string::npos||raw.find("//")!=std::string::npos||
               raw.compare(0,requiredPrefix.size(),requiredPrefix)!=0) bad("CATALOG_PATH",where,"Catalog path must be a safe repository-relative source path");
            const std::filesystem::path path(raw);
            if(path.is_absolute()) bad("CATALOG_PATH",where,"Absolute catalog path is forbidden");
            for(const auto& part:path) if(part=="."||part==".."||part.empty()) bad("CATALOG_PATH",where,"Dot or empty catalog path component is forbidden");
            return raw;
        };
        const auto& scope=at(catalog,"scope");const auto sp=p+"/scope";
        shape(scope,sp,{"entry_count","first_level","last_level","wbs_owners"});
        const auto count=integer(at(scope,"entry_count"),sp+"/entry_count",1,105);
        if(integer(at(scope,"first_level"),sp+"/first_level",1,105)!=1||
           integer(at(scope,"last_level"),sp+"/last_level",1,105)!=count) bad("CATALOG_LEVEL",sp,"Catalog levels must cover 1 through entry_count");
        strings(at(scope,"wbs_owners"),sp+"/wbs_owners",true);
        if(at(scope,"wbs_owners").array().empty()||at(scope,"wbs_owners").array().size()>3) bad("CATALOG_OWNER",sp,"Expected bounded WBS owners");
        const auto& map=at(catalog,"inventory_map");shape(map,p+"/inventory_map",{"path","sha256"});
        safePath(at(map,"path"),p+"/inventory_map/path","Results/");hashText(at(map,"sha256"),p+"/inventory_map/sha256");
        const auto& entries=array(at(catalog,"entries"),p+"/entries",105);
        const auto& bindings=array(at(catalog,"inventory_bindings"),p+"/inventory_bindings",105);
        if(entries.size()!=static_cast<std::size_t>(count)||bindings.size()!=entries.size()) bad("CATALOG_COUNT",p,"Catalog entries and bindings must match declared count");
        std::set<std::string> workbooks,paths,owners;std::set<std::int64_t> levels;
        for(std::size_t i=0;i<entries.size();++i) {
            const auto ep=p+"/entries/"+std::to_string(i),bp=p+"/inventory_bindings/"+std::to_string(i);
            const auto& entry=entries[i];const auto& binding=bindings[i];
            shape(entry,ep,{"admitted","catalog_role","conversion_status","imported","pdf","playable_projection","review","runtime_admitted","runtime_eligible","stable_identity_status","txt","unresolved_playable_fields","whole_workbook_complete","workbook_id"},
                  {"source_specific_ambiguities","representative_item_id","representative_status","reserved_playable_identity_ranges"});
            shape(binding,bp,{"instructional_family","level","pair_status","pdf_path","pdf_sha256","section","source_specific_ambiguities","txt_path","txt_sha256","wbs_owner","workbook_id"});
            const auto level=integer(at(binding,"level"),bp+"/level",1,105);
            if(!levels.insert(level).second) bad("CATALOG_DUPLICATE",bp+"/level","Level appears more than once");
            if(level!=static_cast<std::int64_t>(i+1)) bad("CATALOG_LEVEL",bp+"/level","Bindings must be in consecutive level order");
            std::ostringstream workbook;workbook<<"fg:workbook:"<<std::setw(6)<<std::setfill('0')<<level;
            const auto& id=text(at(entry,"workbook_id"),ep+"/workbook_id");
            if(!workbooks.insert(id).second) bad("CATALOG_DUPLICATE",ep+"/workbook_id","Workbook appears more than once");
            if(id!=workbook.str()||at(binding,"workbook_id")!=at(entry,"workbook_id")) bad("CATALOG_LEVEL",ep+"/workbook_id","Workbook identity does not match binding level");
            for(auto key:{"admitted","imported","runtime_admitted","runtime_eligible","whole_workbook_complete"}) falseOnly(at(entry,key),ep+"/"+key,"CATALOG_NOT_ADMITTED");
            oneOf(at(entry,"catalog_role"),ep+"/catalog_role",{"read_only_source_preservation"});
            oneOf(at(entry,"review"),ep+"/review",{"Pending"});
            oneOf(at(entry,"conversion_status"),ep+"/conversion_status",{"not_converted","converted_candidate"});
            oneOf(at(entry,"stable_identity_status"),ep+"/stable_identity_status",{"evidenced_source_only","accepted_detailed_workbook"});
            strings(at(entry,"unresolved_playable_fields"),ep+"/unresolved_playable_fields",true);
            if(at(entry,"unresolved_playable_fields").array().empty()) bad("CATALOG_NOT_ADMITTED",ep,"Source-only entry must retain playable gaps");
            if(const auto ambiguities=entry.find("source_specific_ambiguities")) strings(*ambiguities,ep+"/source_specific_ambiguities");
            if(const auto representative=entry.find("representative_item_id")) {
                if(!entry.find("representative_status")) bad("CATALOG_SHAPE",ep,"Representative status is required with representative item");
                if(representative->null()) oneOf(at(entry,"representative_status"),ep+"/representative_status",{"outside_representative_package"});
                else { text(*representative,ep+"/representative_item_id");oneOf(at(entry,"representative_status"),ep+"/representative_status",{"frozen_representative_record"}); }
            } else if(entry.find("representative_status")) bad("CATALOG_SHAPE",ep,"Representative status has no item");
            if(const auto reserved=entry.find("reserved_playable_identity_ranges")) {
                shape(*reserved,ep+"/reserved_playable_identity_ranges",{"status","items","modules","variants"});
                text(at(*reserved,"status"),ep+"/reserved_playable_identity_ranges/status");
                for(auto key:{"items","modules","variants"}) { strings(at(*reserved,key),ep+"/reserved_playable_identity_ranges/"+key,true);if(at(*reserved,key).array().size()!=2) bad("CATALOG_SHAPE",ep,"Reserved range needs two bounds"); }
            }
            const auto& projection=at(entry,"playable_projection");const auto pp=ep+"/playable_projection";
            if(at(entry,"stable_identity_status").string()=="evidenced_source_only") {
                shape(projection,pp,{"status","events","items","modules","passages","records","variants"});
                oneOf(at(projection,"status"),pp+"/status",{"explicitly_empty_unresolved"});
                for(auto key:{"events","items","modules","passages","records","variants"}) if(!array(at(projection,key),pp+"/"+key,limits.events).empty()) bad("CATALOG_NOT_ADMITTED",pp,"Source-only projection must be empty");
            } else {
                shape(projection,pp,{"status","accepted_detailed_record_ids","new_events","new_items","new_modules","new_passages","new_records","new_variants"});
                oneOf(at(projection,"status"),pp+"/status",{"existing_detailed_records_unchanged_no_new_projection"});
                strings(at(projection,"accepted_detailed_record_ids"),pp+"/accepted_detailed_record_ids",true);
                if(at(projection,"accepted_detailed_record_ids").array().empty()||at(projection,"accepted_detailed_record_ids").array().size()>limits.records) bad("CATALOG_COUNT",pp,"Detailed source reference list is empty or unbounded");
                for(auto key:{"new_events","new_items","new_modules","new_passages","new_records","new_variants"}) if(!array(at(projection,key),pp+"/"+key,limits.events).empty()) bad("CATALOG_NOT_ADMITTED",pp,"Catalog cannot add playable projection");
            }
            const auto& txt=at(entry,"txt");const auto tp=ep+"/txt";
            shape(txt,tp,{"bytes","encoding","line_count","lines","newline","path","sha256","terminal_newline"});
            oneOf(at(txt,"encoding"),tp+"/encoding",{"utf-8"});oneOf(at(txt,"newline"),tp+"/newline",{"LF","CRLF","CR"});boolean(at(txt,"terminal_newline"),tp+"/terminal_newline");
            const auto txtPath=safePath(at(txt,"path"),tp+"/path","Notes/music/guitar project/TXT version/");
            if(!paths.insert(txtPath).second) bad("CATALOG_DUPLICATE",tp+"/path","Source path reused");
            hashText(at(txt,"sha256"),tp+"/sha256");const auto txtBytes=integer(at(txt,"bytes"),tp+"/bytes",1,static_cast<std::int64_t>(limits.assetBytes));
            const auto lineCount=integer(at(txt,"line_count"),tp+"/line_count",1,100000);
            const auto& lines=array(at(txt,"lines"),tp+"/lines",100000);
            if(lines.size()!=static_cast<std::size_t>(lineCount)) bad("CATALOG_COUNT",tp,"TXT line count differs");
            const auto newline=at(txt,"newline").string()=="CRLF"?"\r\n":at(txt,"newline").string()=="CR"?"\r":"\n";
            std::string reconstructed;
            for(std::size_t line=0;line<lines.size();++line) {
                const auto lp=tp+"/lines/"+std::to_string(line);shape(lines[line],lp,{"line_number","text"});
                if(integer(at(lines[line],"line_number"),lp+"/line_number",1,100000)!=static_cast<std::int64_t>(line+1)) bad("CATALOG_LEVEL",lp,"TXT lines must be sequential");
                if(line) reconstructed+=newline;
                reconstructed+=text(at(lines[line],"text"),lp+"/text",true);
            }
            if(at(txt,"terminal_newline").boolean()) reconstructed+=newline;
            if(reconstructed.size()!=static_cast<std::size_t>(txtBytes)||sha256(reconstructed)!=at(txt,"sha256").string()) bad("CATALOG_SOURCE_HASH",tp,"Reconstructed TXT bytes differ from declared identity");
            const auto& pdf=at(entry,"pdf");const auto dp=ep+"/pdf";
            shape(pdf,dp,{"authoritative_scope","bytes","extraction","page_count","pages","path","sha256"});
            text(at(pdf,"authoritative_scope"),dp+"/authoritative_scope");
            const auto pdfPath=safePath(at(pdf,"path"),dp+"/path","Notes/music/guitar project/PDF version/");
            if(!paths.insert(pdfPath).second) bad("CATALOG_DUPLICATE",dp+"/path","Source path reused");
            integer(at(pdf,"bytes"),dp+"/bytes",1,static_cast<std::int64_t>(limits.assetBytes));hashText(at(pdf,"sha256"),dp+"/sha256");
            const auto pageCount=integer(at(pdf,"page_count"),dp+"/page_count",1,1000);
            const auto& pages=array(at(pdf,"pages"),dp+"/pages",1000);
            if(pages.size()!=static_cast<std::size_t>(pageCount)) bad("CATALOG_COUNT",dp,"PDF page count differs");
            const auto& extraction=at(pdf,"extraction");shape(extraction,dp+"/extraction",{"engine","limitations","version"});
            for(auto key:{"engine","limitations","version"}) text(at(extraction,key),dp+"/extraction/"+key);
            for(std::size_t page=0;page<pages.size();++page) {
                const auto qp=dp+"/pages/"+std::to_string(page);shape(pages[page],qp,{"extracted_text","extracted_text_sha256","full_pdf_sha256","page_number"});
                if(integer(at(pages[page],"page_number"),qp+"/page_number",1,1000)!=static_cast<std::int64_t>(page+1)) bad("CATALOG_LEVEL",qp,"PDF pages must be sequential");
                hashText(at(pages[page],"extracted_text_sha256"),qp+"/extracted_text_sha256");hashText(at(pages[page],"full_pdf_sha256"),qp+"/full_pdf_sha256");
                if(at(pages[page],"full_pdf_sha256")!=at(pdf,"sha256")||sha256(text(at(pages[page],"extracted_text"),qp+"/extracted_text",true))!=at(pages[page],"extracted_text_sha256").string()) bad("CATALOG_SOURCE_HASH",qp,"PDF page metadata differs from declared identity");
            }
            if(at(binding,"txt_path").string()!=txtPath||at(binding,"pdf_path").string()!=pdfPath||at(binding,"txt_sha256")!=at(txt,"sha256")||at(binding,"pdf_sha256")!=at(pdf,"sha256")) bad("CATALOG_BINDING",bp,"Source pair binding differs from entry identity");
            oneOf(at(binding,"pair_status"),bp+"/pair_status",{"exact_stem_pair"});
            text(at(binding,"instructional_family"),bp+"/instructional_family");text(at(binding,"section"),bp+"/section");
            strings(at(binding,"source_specific_ambiguities"),bp+"/source_specific_ambiguities");
            const auto owner=text(at(binding,"wbs_owner"),bp+"/wbs_owner");
            if(owner!="2.3.1.1.1"&&owner!="2.3.1.2.1"&&owner!="2.3.1.3.1") bad("CATALOG_OWNER",bp,"Unknown source conversion owner");
            owners.insert(owner);
        }
        std::set<std::string> declaredOwners;for(const auto& owner:at(scope,"wbs_owners").array()) declaredOwners.insert(owner.string());
        if(owners!=declaredOwners) bad("CATALOG_OWNER",sp,"Declared owners differ from catalog bindings");
    }
    void catalogBinding() {
        const auto p=package.find("workbook_catalog"),r=registry.find("workbook_catalog"),f=profile.find("workbook_catalog");
        if(!curriculum) {
            if(p||r||f) bad("UNKNOWN_FIELD","/workbook_catalog","Workbook catalog requires schema1 curriculum candidate");
            return;
        }
        if((p!=nullptr)!=(r!=nullptr)||(p!=nullptr)!=(f!=nullptr)) bad("CATALOG_BINDING","/workbook_catalog","Package, registry and profile must all carry the same catalog or all omit it");
        if(!p)return;
        catalogShape(*p,"/package/workbook_catalog");
        compare(*p,*r,"/registry/workbook_catalog","CATALOG_FIDELITY");
        compare(*p,*f,"/profile/workbook_catalog","CATALOG_FIDELITY");
    }
    void indexEntities(const J& j,std::map<std::string,const J*>& dest,const std::string& p,bool allowCatalog=false) {
        if(allowCatalog) shape(j,p,{"identity_version","entities","rules"},{"workbook_catalog"});
        else shape(j,p,{"identity_version","entities","rules"});
        text(at(j,"rules"),p+"/rules"); integer(at(j,"identity_version"),p+"/identity_version",1,1);
        for(const auto& e:array(at(j,"entities"),p+"/entities",limits.entities)) {
            checkpoint();
            shape(e,p,{"id","kind","parent","label"}); const auto id=text(at(e,"id"),p+"/id");
            oneOf(at(e,"kind"),p+"/kind",{"course","workbook","module","item","variant"}); nullableString(at(e,"parent"),p+"/parent"); text(at(e,"label"),p+"/label");
            if(!dest.emplace(id,&e).second) issue("DUPLICATE_ID",p+"/"+id,"Duplicate identity entity");
        }
    }
    void identityGraph() {
        const std::map<std::string,std::string> parents{{"workbook","course"},{"module","workbook"},{"item","module"},{"variant","item"}};
        for(const auto& kv:entities) {
            checkpoint();
            const auto& e=*kv.second; const auto kind=at(e,"kind").string(); const auto& parent=at(e,"parent");
            if(kind=="course") { if(!parent.null()) issue("IDENTITY_PARENT_KIND","/registry/"+kv.first,"Course must be a root"); }
            else if(parent.null()||!entities.count(parent.string())) issue("IDENTITY_DANGLING","/registry/"+kv.first,"Required parent is missing");
            else if(at(*entities.at(parent.string()),"kind").string()!=parents.at(kind)) issue("IDENTITY_PARENT_KIND","/registry/"+kv.first,"Incorrect parent kind");
            const auto prefix="fg:"+kind+":";
            if(kv.first.compare(0,prefix.size(),prefix)!=0||kv.first.size()==prefix.size()) issue("IDENTITY_NAMESPACE","/registry/"+kv.first,"ID must use its stable kind namespace");
        }
        // Iterative walk avoids stack overflow on adversarial long parent chains.
        std::set<std::string> complete;
        for(const auto& kv:entities) {
            checkpoint();
            std::set<std::string> chain; std::string id=kv.first;
            while(entities.count(id)&&!complete.count(id)) {
                if(!chain.insert(id).second) { issue("IDENTITY_CYCLE","/registry/"+id,"Parent graph contains a cycle"); break; }
                const auto& p=at(*entities.at(id),"parent"); if(p.null()) break; id=p.string();
            }
            complete.insert(chain.begin(),chain.end());
        }
        coverage(keys(entities),keys(expectedEntities),"/registry/entities");
        for(const auto& kv:entities) if(expectedEntities.count(kv.first)) compare(*kv.second,*expectedEntities.at(kv.first),"/registry/entities/"+kv.first,"IDENTITY_FIDELITY");
    }
    void validateBaseline() {
        if(identityBaseline.null()||allocationBaseline.null()||lineageBaseline.null()) bad("BASELINE_REQUIRED","/authority","Schema1 requires identity, allocation and current lineage baselines");
        indexEntities(identityBaseline,baselineEntities,"/identity_baseline");
        shape(allocationBaseline,"/allocation_baseline",{"version","authority","records"});
        oneOf(at(allocationBaseline,"version"),"/allocation_baseline/version",{"control-allocation.1"});
        text(at(allocationBaseline,"authority"),"/allocation_baseline/authority");
        shape(lineageBaseline,"/lineage_baseline",{"version","records"});
        oneOf(at(lineageBaseline,"version"),"/lineage_baseline/version",{"lineage-baseline.1"});
        const auto& allocations=at(allocationBaseline,"records");
        const auto& heads=at(lineageBaseline,"records");
        if(!allocations.isObject()||!heads.isObject()||allocations.object().size()>limits.records||heads.object().size()>limits.records) bad("BASELINE_SHAPE","/baseline","Expected bounded item maps");
        std::set<std::string> items,variants;
        const std::map<std::string,std::string> parents{{"workbook","course"},{"module","workbook"},{"item","module"},{"variant","item"}};
        for(const auto& entry:baselineEntities) {
            const auto& entity=*entry.second;const auto kind=at(entity,"kind").string();const auto& parent=at(entity,"parent");
            const auto prefix="fg:"+kind+":";
            if(entry.first.size()<=prefix.size()||entry.first.compare(0,prefix.size(),prefix)!=0) bad("BASELINE_IDENTITY","/baseline/"+entry.first,"Invalid identity namespace");
            if(kind=="course") {if(!parent.null()) bad("BASELINE_PARENT","/baseline/"+entry.first,"Course must have no parent");}
            else if(parent.null()||!baselineEntities.count(parent.string())||at(*baselineEntities.at(parent.string()),"kind").string()!=parents.at(kind)) bad("BASELINE_PARENT","/baseline/"+entry.first,"Invalid baseline parent kind");
            if(kind=="item")items.insert(entry.first);
            if(kind=="variant")variants.insert(entry.first);
        }
        if(items!=objectKeys(allocations)||items!=objectKeys(heads)) bad("BASELINE_COVERAGE","/baseline","Baseline item entities, allocations and lineage heads must match exactly");
        for(const auto& item:allocations.object()) {
            const auto& a=item.second;const auto path="/allocation_baseline/"+item.first;
            shape(a,path,{"legacy_level","occurrences","variants"});integer(at(a,"legacy_level"),path,1,105);
            stringMap(at(a,"occurrences"),path);stringMap(at(a,"variants"),path);
            const auto& head=at(heads,item.first);shape(head,path,{"content_revision","record_sha256"});
            integer(at(head,"content_revision"),path,1,std::numeric_limits<int>::max());hashText(at(head,"record_sha256"),path);
            for(const auto& occurrence:at(a,"occurrences").object()) {
                const auto id=occurrence.second.string();const auto prefix=item.first+":event:";
                if(id.size()<=prefix.size()||id.compare(0,prefix.size(),prefix)!=0||!baselineOccurrences.emplace(id,item.first).second) bad("BASELINE_OCCURRENCE",path,"Occurrences must be unique and scoped to their item");
            }
            for(const auto& variant:at(a,"variants").object()) {
                const auto id=variant.second.string();
                if(!variants.count(id)||at(*baselineEntities.at(id),"parent")!=J(item.first)||!baselineVariants.emplace(id,item.first).second) bad("BASELINE_VARIANT",path,"Variant must be uniquely allocated under its registered item");
            }
        }
        std::set<std::string> allocatedBaselineVariants;
        for(const auto& entry:baselineVariants) allocatedBaselineVariants.insert(entry.first);
        if(allocatedBaselineVariants!=variants) bad("BASELINE_VARIANT_COVERAGE","/baseline","Every reserved variant needs an exact allocation");
        for(const auto& entry:predecessorRecords) {
            const auto& prior=entry.second;const auto id=entry.first;
            if(!items.count(id)) bad("PREDECESSOR_HEAD","/predecessor/"+id,"Predecessor item is absent from cumulative head");
            const auto& head=at(heads,id);const auto& a=at(allocations,id);
            if(at(head,"record_sha256").string()!=predecessorHashes.at(id)||at(head,"content_revision")!=at(prior,"content_revision")) bad("PREDECESSOR_HEAD","/predecessor/"+id,"Predecessor is not the current revision and digest");
            const auto module=at(prior,"module_id").string();
            if(at(*baselineEntities.at(id),"parent")!=at(prior,"module_id")||!baselineEntities.count(module)||at(*baselineEntities.at(module),"parent")!=at(prior,"workbook_id")||at(a,"legacy_level")!=at(prior,"legacy_level")) bad("PREDECESSOR_MEMBERSHIP","/predecessor/"+id,"Predecessor parent/source identity differs from baseline");
            std::set<std::string> events,allocatedEvents,priorVariants,allocatedVariants;
            for(const auto& event:array(at(prior,"events"),"/predecessor/events",limits.events)) if(!events.insert(text(at(event,"event_id"),"/predecessor/event_id")).second)bad("PREDECESSOR_MEMBERSHIP","/predecessor/"+id,"Predecessor repeats an event identity");
            for(const auto& event:at(a,"occurrences").object()) allocatedEvents.insert(event.second.string());
            for(const auto& variant:array(at(prior,"variants"),"/predecessor/variants",limits.entities)) if(!priorVariants.insert(text(at(variant,"id"),"/predecessor/variant_id")).second)bad("PREDECESSOR_MEMBERSHIP","/predecessor/"+id,"Predecessor repeats a variant identity");
            for(const auto& variant:at(a,"variants").object()) allocatedVariants.insert(variant.second.string());
            if(events!=allocatedEvents||priorVariants!=allocatedVariants) bad("PREDECESSOR_MEMBERSHIP","/predecessor/"+id,"Predecessor occurrences/variants differ from cumulative reservation");
        }
    }
    void validateLineage(const J& record,const J& allocated) {
        const auto id=at(record,"id").string();const auto path="/records/"+id+"/lineage";const auto& lineage=at(record,"lineage");
        if(!lineage.isObject()||!lineage.find("kind"))bad("LINEAGE_KIND",path,"Explicit lineage kind is required");
        const auto kind=text(at(lineage,"kind"),path);const bool known=baselineEntities.count(id)!=0;
        // Repackaging an exact current immutable record preserves its original lineage and revision.
        const bool unchanged=known&&predecessorRecords.count(id)&&record==predecessorRecords.at(id);
        if(unchanged) {
            if(kind=="new") {
                shape(lineage,path,{"kind"});
                if(at(record,"content_revision")!=J::fromInteger(1))bad("LINEAGE_NEW",path,"Original new-record lineage requires revision1");
            } else if(kind=="revision") {
                shape(lineage,path,{"kind","predecessor_sha256","predecessor_revision"});hashText(at(lineage,"predecessor_sha256"),path);
                const auto previous=integer(at(lineage,"predecessor_revision"),path,1,std::numeric_limits<int>::max());
                if(previous==std::numeric_limits<int>::max()||integer(at(record,"content_revision"),path,1,std::numeric_limits<int>::max())!=previous+1)bad("LINEAGE_REVISION",path,"Original revision lineage is inconsistent");
            } else bad("LINEAGE_KIND",path,"Unsupported original lineage kind");
            if(allocated!=at(at(allocationBaseline,"records"),id))bad("ALLOCATION_REMAP",path,"Exact current record reuse must retain its complete allocation");
            return;
        }
        if(kind=="new") {
            shape(lineage,path,{"kind"});
            if(known||predecessorRecords.count(id)||at(record,"content_revision")!=J::fromInteger(1))bad("LINEAGE_NEW",path,"New items must be unallocated and begin at revision1");
        } else if(kind=="revision") {
            shape(lineage,path,{"kind","predecessor_sha256","predecessor_revision"});hashText(at(lineage,"predecessor_sha256"),path);
            const auto rev=integer(at(lineage,"predecessor_revision"),path,1,std::numeric_limits<int>::max());
            if(!known||!predecessorRecords.count(id)||!predecessorHashes.count(id)||at(lineage,"predecessor_sha256").string()!=predecessorHashes.at(id)||at(predecessorRecords.at(id),"content_revision")!=at(lineage,"predecessor_revision"))bad("LINEAGE_PREDECESSOR",path,"Revision requires exact current predecessor identity/digest/revision");
            if(rev==std::numeric_limits<int>::max()||integer(at(record,"content_revision"),path,1,std::numeric_limits<int>::max())!=rev+1)bad("LINEAGE_REVISION",path,"Content revision must advance exactly once without overflow");
            const auto& previous=at(at(allocationBaseline,"records"),id);
            for(const auto key:{"occurrences","variants"})for(const auto& entry:at(previous,key).object()) {
                const auto found=at(allocated,key).find(entry.first);
                if(!found||*found!=entry.second)bad("ALLOCATION_REMAP",path,"Existing occurrence/variant key may not be removed or reassigned");
            }
        } else bad("LINEAGE_KIND",path,"Unsupported lineage kind");
        for(const auto& entry:at(allocated,"occurrences").object()) {
            const auto found=baselineOccurrences.find(entry.second.string());
            if(found!=baselineOccurrences.end()&&found->second!=id)bad("ALLOCATION_RESERVED",path,"Occurrence was previously allocated to another item");
        }
        for(const auto& entry:at(allocated,"variants").object()) {
            const auto found=baselineVariants.find(entry.second.string());
            if(found!=baselineVariants.end()&&found->second!=id)bad("ALLOCATION_RESERVED",path,"Variant was previously allocated to another item");
        }
    }
    void authority() {
        std::set<std::string> artifactPaths, baselineRoles;
        bool manifestBound=false,acceptanceBound=false,predecessorBound=false,allocationBound=false;
        for(const auto& a:array(at(profile,"authority_artifacts"),"/profile/authority_artifacts",limits.sources)) {
            checkpoint();
            shape(a,"/profile/authority_artifacts",{"path","sha256","role"}); const auto path=text(at(a,"path"),"/profile/authority_artifacts/path"); hashText(at(a,"sha256"),"/profile/authority_artifacts/sha256"); text(at(a,"role"),"/profile/authority_artifacts/role");
            if(!artifactPaths.insert(path).second) bad("AUTHORITY_DUPLICATE",path,"Duplicate authority artifact");
            const bool archived=input.installedRuntime&&input.installedRuntime->hasArchivedEvidence(path);
            if(archived){
                if(std::filesystem::canonical(input.sourceRoot)!=input.installedRuntime->packageRoot())bad("ARCHIVE_ROOT",path,"Archived authority belongs to another package");
                input.installedRuntime->verifyArchivedEvidence(path,at(a,"sha256").string());
                archivedEvidence.emplace(path,a);
            }else asset(path,at(a,"sha256").string());
            if(candidate&&at(a,"role").string()=="predecessor_validation") {
                if(predecessorBound&&!curriculum) bad("PREDECESSOR_DUPLICATE",path,"Only one predecessor report is supported");
                J report;
                if(archived){
                    const auto snapshot=input.installedRuntime->readSemanticProjection(path,at(a,"sha256").string());
                    report=J::Object{{"validator_version",snapshot.validatorVersion},{"valid_reference",snapshot.validReference},{"records",snapshot.records}};
                }else report=json::parse(asset(path,at(a,"sha256").string(),true),limits.json);
                checkpoint();
                if(!report.find("validator_version")||text(at(report,"validator_version"),path)!="canonical-validator.1"||!report.find("valid_reference")||!at(report,"valid_reference").isBool()||!at(report,"valid_reference").boolean()) bad("PREDECESSOR_REPORT",path,"Require the valid original canonical-validator.1 report");
                for(const auto& record:array(at(report,"records"),path+"/records",limits.records)) {
                    checkpoint();
                    const auto id=text(at(record,"id"),path+"/id");hashText(at(record,"record_sha256"),path+"/record_sha256");
                    if(sha256(json::stringify(at(record,"preserved_record")))!=at(record,"record_sha256").string()) bad("PREDECESSOR_RECORD_HASH",path,"Original report serialization digest is inconsistent");
                    if(!predecessorHashes.emplace(id,at(record,"record_sha256").string()).second) bad("PREDECESSOR_DUPLICATE",path,"Duplicate predecessor item");
                    if(curriculum) {
                        const auto& preserved=at(record,"preserved_record");
                        if(at(preserved,"id")!=at(record,"id")||at(preserved,"content_revision")!=at(record,"content_revision")) bad("PREDECESSOR_RECORD_IDENTITY",path,"Report identity/revision differs from preserved record");
                        predecessorRecords.emplace(id,preserved);
                    }
                }
                predecessorBound=true;
            }
            if(candidate&&at(a,"role").string()=="candidate_identity_allocation") {
                if(allocationBound) bad("ALLOCATION_DUPLICATE",path,"Only one candidate allocation is supported");
                allocation=json::parse(asset(path,at(a,"sha256").string(),true),limits.json);
                shape(allocation,path,{"version","authority","records"});oneOf(at(allocation,"version"),path,{"control-allocation.1"});text(at(allocation,"authority"),path);
                if(!at(allocation,"records").isObject()) bad("ALLOCATION_SHAPE",path,"Expected explicit item allocations");
                for(const auto& kv:at(allocation,"records").object()) {shape(kv.second,path,{"legacy_level","occurrences","variants"});integer(at(kv.second,"legacy_level"),path,1,105);stringMap(at(kv.second,"occurrences"),path);stringMap(at(kv.second,"variants"),path);}
                allocationBound=true;
            }
            if(curriculum) {
                const auto role=at(a,"role").string();
                J* target=role=="identity_baseline"?&identityBaseline:role=="allocation_baseline"?&allocationBaseline:role=="lineage_baseline"?&lineageBaseline:nullptr;
                if(target) {
                    if(!baselineRoles.insert(role).second) bad("BASELINE_DUPLICATE",path,"Each cumulative baseline role must occur exactly once");
                    *target=json::parse(asset(path,at(a,"sha256").string(),true),limits.json);
                }
            }
            if(at(a,"role").string()=="source_manifest"&&at(a,"sha256")==at(package,"source_manifest_sha256")) manifestBound=true;
            if(at(a,"role").string()=="source_acceptance"&&path==at(package,"source_acceptance").string()) acceptanceBound=true;
        }
        if(!manifestBound||!acceptanceBound) bad("AUTHORITY_BINDING","/profile/authority_artifacts","Required source manifest and source acceptance identities are not bound");
        if(candidate&&((!curriculum&&!predecessorBound)||!allocationBound)) bad("CANDIDATE_AUTHORITY","/profile/authority_artifacts","Candidate requires bound predecessor report and stable allocation");
        if(curriculum) validateBaseline();
        const auto& rp=at(profile,"resource_plan");
        if(!rp.null()) {
            shape(rp,"/profile/resource_plan",{"path","sha256","entry_ids","availability"}); const auto path=text(at(rp,"path"),"/profile/resource_plan/path"); hashText(at(rp,"sha256"),"/profile/resource_plan/sha256");
            strings(at(rp,"entry_ids"),"/profile/resource_plan/entry_ids",true); oneOf(at(rp,"availability"),"/profile/resource_plan/availability",{"required_unsupplied"});
            // The complete actual plan is separately hash-bound. This is not inferred from the two example resource entries.
            asset(path,at(rp,"sha256").string());
        }
    }
    void sourcePassages() {
        const auto& sources=at(package,"sources"); const auto& expected=at(at(profile,"reference_package"),"sources");
        coverage(objectKeys(sources),objectKeys(expected),"/sources");
        for(const auto& kv:sources.object()) guard([&] {
            const auto p="/sources/"+kv.first; const auto& s=kv.second;
            if(!s.isObject()||!s.find("format")) bad("SOURCE_FORMAT",p,"Source format is required");
            oneOf(at(s,"format"),p+"/format",{"txt","pdf"}); const bool txt=at(s,"format").string()=="txt";
            if(txt) shape(s,p,{"path","sha256","format","first_line","last_line","text","text_sha256"});
            else shape(s,p,{"path","sha256","format","page","text","text_sha256"});
            const auto path=text(at(s,"path"),p+"/path"); hashText(at(s,"sha256"),p+"/sha256"); hashText(at(s,"text_sha256"),p+"/text_sha256");
            const auto passage=text(at(s,"text"),p+"/text");
            if(sha256(passage)!=at(s,"text_sha256").string()) bad("SOURCE_TEXT_HASH",p+"/text_sha256","Passage text differs from its hash");
            if(const auto ex=expected.find(kv.first)) compare(s,*ex,p,"SOURCE_FIDELITY");
            auto bytes=asset(path,at(s,"sha256").string(),txt);
            if(txt) {
                const auto first=integer(at(s,"first_line"),p+"/first_line",1,10000000); const auto last=integer(at(s,"last_line"),p+"/last_line",first,10000000);
                // Match retained splitlines line numbering, accepting ordinary CR/LF/CRLF only.
                std::vector<std::string> lines; std::string line;
                for(std::size_t i=0;i<bytes.size();++i) {
                    if(bytes[i]=='\r'||bytes[i]=='\n') { lines.push_back(line); line.clear(); if(bytes[i]=='\r'&&i+1<bytes.size()&&bytes[i+1]=='\n') ++i; }
                    else line+=bytes[i];
                }
                if(!line.empty()) lines.push_back(line);
                if(static_cast<std::uint64_t>(last)>lines.size()) bad("SOURCE_LOCATOR",p,"Line span exceeds actual source");
                std::string actual;
                for(auto i=first;i<=last;++i) { if(i!=first) actual+='\n'; actual+=lines[static_cast<std::size_t>(i-1)]; }
                if(actual!=passage) bad("SOURCE_TEXT_SPAN",p+"/text","Exact TXT span differs from source bytes");
            } else integer(at(s,"page"),p+"/page",1,1000000);
        },"",kv.first);
    }
    music::Span span(const J& j,const std::string& p) { return {rational(at(j,"onset_q"),p+"/onset_q"),rational(at(j,"duration_q"),p+"/duration_q")}; }
    music::Tone mapTone(const J& j,const std::string& p,bool member,const std::string& id,bool& unbound) {
        music::Tone t;
        t.string=static_cast<int>(integer(at(j,"string"),p,1,128)); t.fret=static_cast<int>(integer(at(j,"fret"),p,0,127)); t.midi=static_cast<int>(integer(at(j,"midi"),p,0,127));
        const auto& finger=at(j,"finger"); if(!finger.null()) { if(finger.isString()) t.finger=finger.string(); else t.finger=std::get<json::Number>(finger.data).token; }
        if(!at(j,"spelling").null()) t.spelling=at(j,"spelling").string();
        if(!at(j,"tie_from").null()) t.tieFrom=at(j,"tie_from").string();
        static const std::map<std::string,music::Attack> attacks{{"picked",music::Attack::Picked},{"hammer_on",music::Attack::HammerOn},{"pull_off",music::Attack::PullOff},{"slide_arrival",music::Attack::SlideArrival},{"bend",music::Attack::Bend},{"held",music::Attack::Held},{"blue_third_shade",music::Attack::BlueThirdShade},{"harmonic",music::Attack::Harmonic},{"vibrato",music::Attack::Vibrato}};
        t.authoredTechnique=at(j,"attack").string(); t.attack=attacks.at(t.authoredTechnique);
        if(const auto b=j.find("bend")) {
            music::BendContour contour;
            contour.targetSemitones=*rational(at(*b,"target_semitones"),p+"/bend/target_semitones");
            if(const auto mode=b->find("mode"))
                contour.mode=mode->string()=="prebent_release"?music::BendMode::PrebentRelease:music::BendMode::RiseHoldRelease;
            if(const auto initial=b->find("initial_offset_semitones"))
                contour.initialOffsetSemitones=*rational(*initial,p+"/bend/initial_offset_semitones");
            for(const auto& knot:at(*b,"knots").array())
                contour.knots.push_back({*rational(at(knot,"q"),p+"/bend/knots/q"),
                    *rational(at(knot,"offset_semitones"),p+"/bend/knots/offset_semitones")});
            t.bend=std::move(contour);
            t.bendSemitones=t.bend->targetSemitones;
        }
        if(member) t.memberSpan=span(j,p);
        const auto& roots=at(profile,"degree_roots");
        for(const auto& kv:at(j,"degree_contexts").object()) {
            const auto rootBinding=roots.find(kv.first);
            if(!rootBinding) { unbound=true; issue("DEGREE_ROOT_UNBOUND",p+"/degree_contexts/"+kv.first,"Original degree retained; cannot project a tonal root without an explicit reviewed binding",id,"","","unresolved"); continue; }
            shape(*rootBinding,p+"/degree_roots/"+kv.first,{"root_pitch_class","basis"}); text(at(*rootBinding,"basis"),p+"/degree_roots/basis");
            music::Degree d; d.context=kv.first; d.sourceLabel=at(kv.second,"source_label").string();
            d.rootPitchClass=static_cast<int>(integer(at(*rootBinding,"root_pitch_class"),p+"/root_pitch_class",0,11)); d.ordinal=static_cast<int>(integer(at(kv.second,"ordinal"),p,1,128)); d.alteration=static_cast<int>(integer(at(kv.second,"alteration"),p,-2,2)); t.degrees.push_back(std::move(d));
        }
        return t;
    }
    void refs(const J& r,const std::string& id) {
        std::set<std::string> declared;
        for(const auto& a:at(r,"source_refs").array()) {
            declared.insert(a.string()); if(!at(package,"sources").find(a.string())) issue("SOURCE_REFERENCE_DANGLING","/source_refs",a.string(),id);
        }
        auto ref=[&](const J& j,const std::string& p) { if(!declared.count(j.string())) issue("SOURCE_REFERENCE_UNDECLARED",p,j.string(),id); };
        for(const auto& a:at(r,"authored_text_refs").array()) ref(a,"/authored_text_refs");
        if(!at(r,"rubric").null()) for(const auto& a:at(at(r,"rubric"),"required_obligations_refs").array()) ref(a,"/rubric/required_obligations_refs");
        const auto& c=at(r,"context");
        for(auto k:{"authored_progression_ref","source_tempo_rules_ref","failed_domain_return_refs"}) if(const auto a=c.find(k)) ref(*a,"/context/"+std::string(k));
        if(const auto a=c.find("held_response_example")) ref(at(*a,"source_ref"),"/context/held_response_example/source_ref");
    }
    static J quantity(const std::optional<Rational>& r) { if(!r)return nullptr; return J::Array{J::fromInteger(r->numerator()),J::fromInteger(r->denominator())}; }
    static J mappedModel(const music::Model& m) {
        J::Array events;
        for(const auto& e:m.events) {
            J::Array tones;
            for(const auto& t:e.tones) {
                J::Array degrees;
                for(const auto& d:t.degrees) degrees.emplace_back(J::Object{{"context",d.context},{"source_label",d.sourceLabel},{"root_pitch_class",J::fromInteger(d.rootPitchClass)},{"ordinal",J::fromInteger(d.ordinal)},{"alteration",J::fromInteger(d.alteration)},{"root_midi",d.rootMidi?J::fromInteger(*d.rootMidi):J{}}});
                J bend;
                if(t.bend) {
                    J::Array knots;
                    for(const auto& knot:t.bend->knots)
                        knots.emplace_back(J::Object{{"q",quantity(knot.q)},{"offset_semitones",quantity(knot.offsetSemitones)}});
                    J::Object fields{{"target_semitones",quantity(t.bend->targetSemitones)}};
                    fields.emplace("knots",std::move(knots));
                    if(t.bend->mode) fields.emplace("mode",*t.bend->mode==music::BendMode::PrebentRelease?"prebent_release":"rise_hold_release");
                    if(t.bend->initialOffsetSemitones) fields.emplace("initial_offset_semitones",quantity(t.bend->initialOffsetSemitones));
                    bend=std::move(fields);
                }
                J::Object mapped{{"string",J::fromInteger(t.string)},{"fret",J::fromInteger(t.fret)},{"midi",J::fromInteger(t.midi)},{"finger",t.finger},{"spelling",t.spelling},{"attack",t.authoredTechnique},{"tie_from",t.tieFrom},{"member_span",t.memberSpan?J(J::Object{{"onset_q",quantity(t.memberSpan->onset)},{"duration_q",quantity(t.memberSpan->duration)}}):J{}},{"sounding_span",nullptr}};
                mapped.emplace("degrees",std::move(degrees));
                if(t.bend) mapped.emplace("bend",std::move(bend));
                tones.emplace_back(std::move(mapped));
            }
            static const std::map<music::Kind,std::string> kinds{{music::Kind::Note,"note"},{music::Kind::Chord,"chord"},{music::Kind::Rest,"rest"},{music::Kind::Contact,"contact"}};
            static const std::map<music::Contact,std::string> contacts{{music::Contact::Pitched,"pitched"},{music::Contact::Muted,"muted"},{music::Contact::Air,"air"},{music::Contact::Release,"release"},{music::Contact::Sustain,"sustain"}};
            J::Object event{{"event_id",e.id},{"source_ref",e.sourceRef},{"kind",kinds.at(e.kind)},{"onset_q",quantity(e.span.onset)},{"duration_q",quantity(e.span.duration)},{"chord_symbol",e.chordSymbol},{"contact",contacts.at(e.contact)},{"pick",e.handDirection}};
            event.emplace("scope_strings",[&]{J::Array a;for(int string:e.scopeStrings)a.push_back(J::fromInteger(string));return a;}());
            event.emplace("tones",std::move(tones));
            events.emplace_back(std::move(event));
        }
        J::Array tuning; for(auto n:m.instrument.openMidi)tuning.push_back(J::fromInteger(n));
        J backing;
        if(m.backing) {
            J::Array sections;
            for(const auto& s:m.backing->sections)sections.emplace_back(J::Object{{"onset_q",quantity(s.onset)},{"duration_q",quantity(s.duration)},
                {"center_pitch_class",J::fromInteger(s.centerPitchClass)},{"midi",J::fromInteger(s.midi)}});
            J::Object fields{{"source_ref",m.backing->sourceRef},{"source_sha256",m.backing->sourceSha256},
                {"event_digest_sha256",m.backing->eventDigestSha256},{"model_choice",m.backing->modelChoice},
                {"level_milli",J::fromInteger(m.backing->levelMilli)}};
            fields.emplace("sections",std::move(sections));
            backing=std::move(fields);
        }
        J::Object mapped{{"capo",J::fromInteger(m.instrument.capo)},{"terminal_q",quantity(m.terminal)},{"measures",J::Array{}}};
        mapped.emplace("tuning_open_midi",std::move(tuning));
        mapped.emplace("events",std::move(events));
        mapped.emplace("backing_drone",std::move(backing));
        return J(std::move(mapped));
    }
    static Rational positive(const J& j,const std::string& p) {
        const auto value=rational(j,p);if(!value||*value==Rational{})bad("POSITIVE_RATIONAL",p,"Expected explicit positive reduced rational");return *value;
    }
    void projectVariants(const J& r,const RecordResult& rr,const std::set<std::string>& unboundEvents) {
        const auto id=rr.id;const auto p="/records/"+id;const auto& scope=at(r,"control_scope");
        if(curriculum)shape(scope,p+"/control_scope",{"local_case","extent","whole_workbook_complete","source_event_count","basis_refs","unresolved"});
        else shape(scope,p+"/control_scope",{"local_case","extent","whole_workbook_complete","source_event_count","basis_refs","unresolved","proposal_record_sha256"});
        text(at(scope,"local_case"),p);oneOf(at(scope,"extent"),p,{"complete_selected_case","selected_illustration","task_reference"});falseOnly(at(scope,"whole_workbook_complete"),p,"WORKBOOK_NOT_COMPLETE");
        const auto count=integer(at(scope,"source_event_count"),p,0,static_cast<std::int64_t>(limits.events));
        if(static_cast<std::uint64_t>(count)!=rr.source.events.size())bad("CONTROL_EVENT_COVERAGE",p,"Declared selected occurrence count differs from actual events");
        strings(at(scope,"unresolved"),p+"/control_scope/unresolved");
        if(!curriculum) {
            hashText(at(scope,"proposal_record_sha256"),p);
            if(!predecessorHashes.count(id)||predecessorHashes.at(id)!=at(scope,"proposal_record_sha256").string())bad("PREDECESSOR_IDENTITY",p,"Candidate predecessor differs from independently bound original report");
        }
        auto sourceRefs=[&](const J& values,const std::string& path) {
            strings(values,path,true);if(values.array().empty())bad("SOURCE_BASIS_EMPTY",path,"Explicit source basis is required");
            for(const auto& ref:values.array())if(std::find(rr.source.sourceRefs.begin(),rr.source.sourceRefs.end(),ref.string())==rr.source.sourceRefs.end())bad("SOURCE_REFERENCE_UNDECLARED",path,"Variant/scope source must be declared by its parent item");
        };
        sourceRefs(at(scope,"basis_refs"),p+"/control_scope/basis_refs");
        if(!allocation.find("records")||!at(allocation,"records").find(id))bad("ALLOCATION_ITEM",p,"Item is absent from bound explicit allocation");
        const auto& allocated=at(at(allocation,"records"),id);
        if(at(allocated,"legacy_level")!=at(r,"legacy_level"))bad("ALLOCATION_LEVEL",p,"Allocated source level differs");
        if(curriculum)validateLineage(r,allocated);
        std::set<std::string> baseIDs,allocatedIDs,covered,allocatedVariants,observedVariants;
        std::map<std::string,std::size_t> indexes;
        for(std::size_t i=0;i<rr.source.events.size();++i){baseIDs.insert(rr.source.events[i].id);indexes.emplace(rr.source.events[i].id,i);}
        for(const auto& kv:at(allocated,"occurrences").object())if(!allocatedIDs.insert(kv.second.string()).second)bad("ALLOCATION_DUPLICATE",p,"Occurrence IDs must be unique in allocation");
        if(baseIDs!=allocatedIDs)bad("ALLOCATION_EVENTS",p,"Candidate occurrence IDs differ from bound allocation");
        for(const auto& kv:at(allocated,"variants").object())if(!allocatedVariants.insert(kv.second.string()).second)bad("ALLOCATION_DUPLICATE",p,"Variant IDs must be unique in allocation");
        const auto& variants=array(at(r,"variants"),p+"/variants",limits.entities);if(variants.empty())bad("VARIANT_EMPTY",p,"Each candidate control requires an explicit variant");
        for(const auto& v:variants) {
            checkpoint();
            shape(v,p+"/variants",{"id","label","event_ids","source_refs","route","pick_start","pick_start_origin","accent_policy","role","grouping","tail_pause","unresolved"},{"backing_drone"});
            const auto vid=text(at(v,"id"),p+"/variants/id");const auto vp=p+"/variants/"+vid;
            if(usedVariants.size()>=limits.entities)bad("VARIANT_COUNT_LIMIT",vp,"Aggregate variant count exceeds declared entity limit");
            if(!usedVariants.insert(vid).second)bad("VARIANT_DUPLICATE",vp,"Variant identity appears more than once");observedVariants.insert(vid);
            if(!entities.count(vid)||at(*entities.at(vid),"kind").string()!="variant"||at(*entities.at(vid),"parent").null()||at(*entities.at(vid),"parent").string()!=id)bad("VARIANT_PARENT",vp,"Variant must be registered under its original item");
            const auto label=text(at(v,"label"),vp+"/label");text(at(v,"route"),vp+"/route");
            const auto mapping=at(allocated,"variants").find(label);
            if(!mapping||mapping->string()!=vid)bad("VARIANT_ALLOCATION",vp,"Variant logical key and identity differ from bound allocation");
            sourceRefs(at(v,"source_refs"),vp+"/source_refs");strings(at(v,"event_ids"),vp+"/event_ids",true);strings(at(v,"unresolved"),vp+"/unresolved");
            oneOf(at(v,"pick_start_origin"),vp+"/pick_start_origin",{"source_authored","learner_configuration","not_applicable"});
            if(!at(v,"pick_start").null())oneOf(at(v,"pick_start"),vp+"/pick_start",{"D","U"});
            if(at(v,"pick_start").null()!=(at(v,"pick_start_origin").string()=="not_applicable"))bad("PICK_ORIGIN",vp,"Pick start and its origin must agree");
            oneOf(at(v,"accent_policy"),vp+"/accent_policy",{"after_crossing","even","source_unspecified"});
            oneOf(at(v,"role"),vp+"/role",{"notation_practice","reference","task","rhythm_mask"});
            const auto& group=at(v,"grouping");shape(group,vp+"/grouping",{"kind","notes_per_beat","beat_unit_q","marking_factor","source_label"});
            oneOf(at(group,"kind"),vp+"/grouping/kind",{"source_event_time","even_subdivision","unresolved","not_applicable"});text(at(group,"source_label"),vp+"/grouping/source_label");
            positive(at(group,"marking_factor"),vp+"/grouping/marking_factor");
            const auto kind=at(group,"kind").string();std::optional<Rational> unit;
            if(!at(group,"beat_unit_q").null())unit=positive(at(group,"beat_unit_q"),vp+"/grouping/beat_unit_q");
            std::int64_t subdivision=0;if(!at(group,"notes_per_beat").null())subdivision=integer(at(group,"notes_per_beat"),vp+"/grouping/notes_per_beat",1,64);
            if(kind=="even_subdivision"&&!subdivision)bad("GROUPING_COUNT",vp,"Even subdivision requires an explicit count");
            if(kind!="even_subdivision"&&(subdivision||unit))bad("GROUPING_UNUSED_BINDING",vp,"Count/beat unit apply only to even-subdivision binding");
            if(at(v,"event_ids").array().size()>limits.events-variantEventTotal)bad("VARIANT_EVENT_LIMIT",vp,"Aggregate variant memberships exceed declared event limit");variantEventTotal+=at(v,"event_ids").array().size();
            VariantResult vr;vr.id=vid;vr.itemId=id;vr.source=rr.source;vr.source.events.clear();vr.source.measures.clear();
            bool bindings=at(v,"unresolved").array().empty()&&kind!="unresolved"&&at(v,"accent_policy").string()!="after_crossing";
            if(id=="fg:item:039901" && vid=="fg:variant:039901" && !v.find("backing_drone"))bindings=false;
            std::optional<std::size_t> last;
            for(const auto& eventID:at(v,"event_ids").array()) {
                const auto eid=eventID.string();if(!indexes.count(eid))bad("VARIANT_MEMBERSHIP",vp,"Variant event is absent or belongs to another item");
                const auto index=indexes.at(eid);if(last&&index<=*last)bad("VARIANT_ORDER",vp,"Variant occurrence order differs from declared source order");last=index;covered.insert(eid);
                const auto& selected=rr.source.events[index];
                if(std::none_of(at(v,"source_refs").array().begin(),at(v,"source_refs").array().end(),[&](const J& ref){return ref.string()==selected.sourceRef;}))bad("VARIANT_EVENT_SOURCE",vp+"/source_refs","Selected event source must belong to this variant basis");
                if(unboundEvents.count(eid))bindings=false;
                vr.source.events.push_back(selected);
            }
            if(kind=="not_applicable"&&!vr.source.events.empty())bad("GROUPING_NOT_APPLICABLE",vp,"Eventful variant cannot discard timing applicability");
            if(kind=="even_subdivision") {
                for(const auto& event:vr.source.events)if(event.kind!=music::Kind::Note||event.tones.size()!=1||event.tones[0].attack!=music::Attack::Picked||!event.tones[0].tieFrom.empty())bad("GROUPING_SPAN_SEMANTICS",vp,"Uniform grouping cannot flatten chords, rests, ties or nonpicked articulations");
                if(!unit)bindings=false;
                else {
                    const auto cancel=std::gcd(unit->numerator(),subdivision);const auto multiplier=subdivision/cancel;
                    if(unit->denominator()>std::numeric_limits<std::int64_t>::max()/multiplier)bad("GROUPING_ARITHMETIC",vp,"Exact duration denominator exceeds representation");
                    const Rational duration(unit->numerator()/cancel,unit->denominator()*multiplier);Rational onset;
                    try {for(auto& event:vr.source.events){event.span={onset,duration};onset=onset+duration;}}
                    catch(const std::overflow_error& error){bad("GROUPING_ARITHMETIC",vp+"/grouping/onset_q",error.what());}
                }
            }
            const auto& pause=at(v,"tail_pause");
            if(!pause.null()) {
                shape(pause,vp+"/tail_pause",{"beats","beat_unit_q","source_ref"});positive(at(pause,"beats"),vp+"/tail_pause/beats");text(at(pause,"source_ref"),vp+"/tail_pause/source_ref");
                if(std::none_of(at(v,"source_refs").array().begin(),at(v,"source_refs").array().end(),[&](const J& ref){return ref==at(pause,"source_ref");}))bad("PAUSE_SOURCE",vp,"Tail-pause source must belong to variant basis");
                if(pause.find("beat_unit_q")->null())bindings=false;else positive(at(pause,"beat_unit_q"),vp+"/tail_pause/beat_unit_q");
                // This projection retains the tail instruction but does not execute a pause operation.
                bindings=false;
            }
            if(const auto drone=v.find("backing_drone")) {
                if(id!="fg:item:039901" || vid!="fg:variant:039901")bad("BACKING_SCOPE",vp,"Version1 backing contract is bounded to Level39 Module F");
                const auto bp=vp+"/backing_drone";
                shape(*drone,bp,{"kind","source_ref","source_sha256","events_sha256","event_ids_sha256","model_choice","timbre","level_milli","lead_level_milli","attack_ms","release_ms","gate","sections"});
                oneOf(at(*drone,"kind"),bp+"/kind",{"level039_module_f_version1"});
                oneOf(at(*drone,"timbre"),bp+"/timbre",{"sine"});
                oneOf(at(*drone,"gate"),bp+"/gate",{"full_section"});
                if(integer(at(*drone,"level_milli"),bp,0,1000)!=80 || integer(at(*drone,"lead_level_milli"),bp,0,1000)!=920
                    || integer(at(*drone,"attack_ms"),bp,0,1000)!=3 || integer(at(*drone,"release_ms"),bp,0,1000)!=10)
                    bad("BACKING_DEFAULT",bp,"Unsupported render default");
                music::BackingLane lane;lane.sourceRef=text(at(*drone,"source_ref"),bp+"/source_ref");
                if(lane.sourceRef!="L39-PDF-PIVOT-P10" || !at(package,"sources").find(lane.sourceRef))bad("BACKING_SOURCE",bp,"Original PDF page 10 source required");
                lane.sourceSha256=text(at(*drone,"source_sha256"),bp+"/source_sha256");hashText(at(*drone,"source_sha256"),bp);
                if(lane.sourceSha256!=at(at(at(package,"sources"),lane.sourceRef),"sha256").string())bad("BACKING_SOURCE_HASH",bp,"Backing source hash differs from pinned PDF");
                hashText(at(*drone,"events_sha256"),bp);hashText(at(*drone,"event_ids_sha256"),bp);
                if(at(*drone,"events_sha256").string()!=sha256(json::stringify(at(r,"events")))
                    || at(*drone,"event_ids_sha256").string()!=sha256(json::stringify(at(v,"event_ids"))))
                    bad("BACKING_CONTACT_HASH",bp,"32-contact source grid or membership differs from binding");
                lane.eventDigestSha256=at(*drone,"events_sha256").string();
                lane.modelChoice=text(at(*drone,"model_choice"),bp+"/model_choice");
                lane.levelMilli=80;
                for(const auto& e:vr.source.events) {
                    if(e.kind!=music::Kind::Note || e.tones.size()!=1 || !e.span.onset || !e.span.duration)
                        bad("BACKING_CONTACT",bp,"Version1 binding requires 32 complete picked notes");
                    const auto& t=e.tones[0];lane.contacts.push_back({e.id,*e.span.onset,*e.span.duration,t.string,t.fret,t.midi});
                }
                for(const auto& section:array(at(*drone,"sections"),bp+"/sections",4)) {
                    shape(section,bp+"/sections",{"onset_q","duration_q","center_pitch_class","midi"});
                    const auto onset=rational(at(section,"onset_q"),bp+"/sections/onset_q");
                    if(!onset)bad("BACKING_ONSET",bp,"Backing onset must be explicit");
                    lane.sections.push_back({*onset,
                        positive(at(section,"duration_q"),bp+"/sections/duration_q"),
                        static_cast<int>(integer(at(section,"center_pitch_class"),bp,0,11)),
                        static_cast<int>(integer(at(section,"midi"),bp,0,127))});
                }
                vr.source.backing=std::move(lane);
            }
            vr.validation=music::validate(vr.source);vr.bindingsComplete=bindings;
            if(vr.validation.model)vr.readiness=music::assessReadiness(*vr.validation.model,{{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true});
            vr.readiness.technicallyRenderable=vr.readiness.technicallyRenderable&&bindings;
            J::Array diagnostics;
            for(const auto& diagnostic:vr.readiness.issues)diagnostics.emplace_back(J::Object{{"code",diagnostic.code},{"field",diagnostic.field},{"event",diagnostic.event},{"message",diagnostic.explanation}});
            if(!bindings){issue("VARIANT_BINDING_UNRESOLVED",vp,"Required variant binding or tail operation is unresolved; note-only projection is not full variant readiness",id,"","","unresolved");diagnostics.emplace_back(J::Object{{"code","variant_binding_unresolved"},{"field",vp},{"event",""},{"message","Required binding/operation remains unresolved"}});}
            for(const auto& diagnostic:vr.validation.issues)if(diagnostic.severity==music::Severity::Contradiction)issue("VARIANT_MODEL_"+diagnostic.code,vp+"/"+diagnostic.field,diagnostic.explanation,id,diagnostic.event);
            variantReports.emplace_back(J::Object{{"variant_id",vid},{"item_id",id},{"valid_reference",vr.validation.validReference()},{"technically_renderable",vr.readiness.technicallyRenderable},{"curriculum_playback_authorized",false},{"bindings_complete",bindings},{"preserved_variant",v},{"model",mappedModel(vr.source)},{"issues",diagnostics}});
            result.variants.push_back(std::move(vr));
        }
        if(covered!=baseIDs)bad("VARIANT_EVENT_COVERAGE",p,"Every selected base occurrence must belong to a declared variant");
        if(observedVariants!=allocatedVariants)bad("VARIANT_ALLOCATION_COVERAGE",p,"Every allocated variant must be represented exactly once");
    }
    void projectRecord(const J& r) {
        const auto id=at(r,"id").string();
        refs(r,id);
        if(!entities.count(id)||at(*entities.at(id),"kind").string()!="item") issue("RECORD_IDENTITY","/id","Record must be registered as an item",id);
        else if(at(*entities.at(id),"parent")!=at(r,"module_id")) issue("RECORD_PARENT","/module_id","Record module differs from registry parent",id);
        const auto module=at(r,"module_id").string();
        if(!entities.count(module)||at(*entities.at(module),"parent")!=at(r,"workbook_id")) issue("RECORD_PARENT","/workbook_id","Record workbook differs from module parent",id);
        if(expectedRecords.count(id)) compare(r,*expectedRecords.at(id),"/records/"+id,"RECORD_FIDELITY",id);
        RecordResult rr; rr.id=id; auto& m=rr.source;
        m.itemId=id; m.schemaVersion=at(package,"schema_version").string(); m.contentVersion=at(package,"content_version").string(); m.contentRevision=static_cast<int>(integer(at(r,"content_revision"),"/content_revision",1,std::numeric_limits<int>::max()));
        m.preservedRecordJson=json::stringify(r); m.proposalExample=!candidate; m.syntheticFixture=at(profile,"classification").string()=="synthetic_fixture";
        if(const auto terminal=r.find("terminal_q")) m.terminal=rational(*terminal,"/records/"+id+"/terminal_q");
        for(const auto& s:at(r,"source_refs").array()) m.sourceRefs.push_back(s.string());
        const auto& c=at(r,"context");
        if(const auto tuning=c.find("tuning_open_midi")) { for(const auto& n:tuning->array()) m.instrument.openMidi.push_back(static_cast<int>(integer(n,"/context/tuning",0,127))); m.instrument.capo=static_cast<int>(integer(at(c,"capo"),"/context/capo",0,127)); }
        bool unbound=false;std::set<std::string> unboundEvents;
        for(const auto& event:at(r,"events").array()) {
            checkpoint();
            bool eventUnbound=false;music::Event e; e.id=at(event,"event_id").string(); const auto p="/records/"+id+"/events/"+e.id;
            if(e.id.size()<=id.size()+7||e.id.compare(0,id.size()+7,id+":event:")!=0) issue("EVENT_IDENTITY",p,"Event identity is outside its item",id,e.id);
            const auto binding=at(profile,"event_sources").find(e.id);
            if(!binding) bad("EVENT_SOURCE_UNBOUND",p+"/source_ref","Event needs an explicit source passage binding in reviewed profile");
            e.sourceRef=text(*binding,p+"/source_ref");
            if(std::find(m.sourceRefs.begin(),m.sourceRefs.end(),e.sourceRef)==m.sourceRefs.end()) bad("EVENT_SOURCE_UNDECLARED",p+"/source_ref","Event source is absent from record source references");
            e.span=span(event,p); const auto kind=at(event,"kind").string();
            if(kind=="note") {e.kind=music::Kind::Note;e.tones.push_back(mapTone(event,p,false,id,eventUnbound));if(const auto pick=event.find("pick"))e.handDirection=pick->string();}
            else if(kind=="chord") {e.kind=music::Kind::Chord;e.chordSymbol=at(event,"symbol").string();if(const auto pick=event.find("pick"))e.handDirection=pick->string();std::size_t i=0;for(const auto& t:at(event,"members").array())e.tones.push_back(mapTone(t,p+"/members/"+std::to_string(i++),true,id,eventUnbound));}
            else if(kind=="rest") {
                e.kind=music::Kind::Rest;
                if(const auto scope=event.find("scope_strings"))
                    for(const auto& value:scope->array())e.scopeStrings.push_back(static_cast<int>(integer(value,p+"/scope_strings",1,128)));
            }
            else {
                e.kind=music::Kind::Contact; const auto k=at(event,"contact").string();
                static const std::map<std::string,music::Contact> contacts{{"pitched",music::Contact::Pitched},{"muted",music::Contact::Muted},{"air",music::Contact::Air},{"release",music::Contact::Release},{"sustain",music::Contact::Sustain}};
                e.contact=contacts.at(k); e.handDirection=at(event,"pick").string();
                if(k=="muted") for(const auto& string:at(event,"scope_strings").array())
                    e.scopeStrings.push_back(static_cast<int>(integer(string,p+"/scope_strings",1,6)));
            }
            if(eventUnbound){unbound=true;unboundEvents.insert(e.id);}
            m.events.push_back(std::move(e));
        }
        rr.validation=music::validate(m);
        auto addMusicIssue=[&](const music::Issue& i) {
            const auto severity=i.severity==music::Severity::Contradiction?"error":i.severity==music::Severity::Unsupported?"unsupported":i.severity==music::Severity::NotAdmitted?"not_admitted":"unresolved";
            std::string source; for(const auto& e:m.events) if(e.id==i.event) {source=e.sourceRef;break;}
            issue("MODEL_"+i.code,i.field,i.explanation,id,i.event,source,severity);
        };
        for(const auto& i:rr.validation.issues)addMusicIssue(i);
        if(rr.validation.model) { rr.readiness=music::assessReadiness(*rr.validation.model,{{music::Attack::Picked,music::Attack::HammerOn,music::Attack::PullOff,music::Attack::Held,music::Attack::SlideArrival,music::Attack::Bend},true,true,true}); if(unbound)rr.readiness.technicallyRenderable=false; }
        // Model readiness repeats structural diagnostics; retain only readiness additions once.
        for(const auto& i:rr.readiness.issues) {
            const auto found=std::find_if(rr.validation.issues.begin(),rr.validation.issues.end(),[&](const auto& a){return std::tie(a.code,a.field,a.event,a.explanation)==std::tie(i.code,i.field,i.event,i.explanation);});
            if(found==rr.validation.issues.end())addMusicIssue(i);
        }
        recordReports.emplace_back(J::Object{{"id",id},{"content_revision",at(r,"content_revision")},{"record_sha256",sha256(m.preservedRecordJson)},{"valid_reference",rr.validation.validReference()},{"musical_valid_reference",rr.validation.validReference()},{"technically_renderable",rr.readiness.technicallyRenderable},{"curriculum_playback_authorized",false},{"degree_projection_complete",!unbound},{"preserved_record",r},{"model",mappedModel(m)}});
        if(candidate) projectVariants(r,rr,unboundEvents);
        result.records.push_back(std::move(rr));
    }
    void execute() {
        checkpoint();
        if(input.expectedProfileSha256.size()!=64||input.expectedProfileSha256.find_first_not_of("0123456789abcdef")!=std::string::npos) bad("PROFILE_HASH_FORMAT","/expected_profile_sha256","Expected independently obtained lowercase SHA-256");
        if(sha256(input.profile)!=input.expectedProfileSha256) bad("PROFILE_HASH","/profile","Profile bytes differ from independently supplied identity");
        auto parse=[&](const std::string& bytes,const std::string& p) {
            try { checkpoint();auto value=json::parse(bytes,limits.json);checkpoint();return value; }
            catch(const json::Error& e) { bad(e.code,p+"/byte/"+std::to_string(e.offset),e.what()); }
        };
        profile=parse(input.profile,"/profile");
        shape(profile,"/profile",{"profile_version","classification","reference_package","reference_registry","event_sources","degree_roots","authority_artifacts","resource_plan"},{"workbook_catalog"});
        oneOf(at(profile,"profile_version"),"/profile/profile_version",{"expected-profile.1"}); oneOf(at(profile,"classification"),"/profile/classification",{"accepted_contract_reference","converted_candidate_reference","synthetic_fixture"});
        if(!at(profile,"event_sources").isObject()||!at(profile,"degree_roots").isObject()) bad("PROFILE_BINDINGS","/profile","Expected event and degree binding objects");
        stringMap(at(profile,"event_sources"),"/profile/event_sources");
        for(const auto& binding:at(profile,"degree_roots").object()) {
            const auto p="/profile/degree_roots/"+binding.first;
            if(binding.first.empty()) bad("EMPTY_STRING",p,"Degree context name is required");
            shape(binding.second,p,{"root_pitch_class","basis"});
            integer(at(binding.second,"root_pitch_class"),p+"/root_pitch_class",0,11);
            text(at(binding.second,"basis"),p+"/basis");
        }
        package=parse(input.package,"/package"); registry=parse(input.registry,"/registry");
        packageShape(package,"/package",true); packageShape(at(profile,"reference_package"),"/profile/reference_package");
        curriculum=at(package,"schema_version").string()=="1.0.0-curriculum-candidate";
        candidate=curriculum||at(package,"schema_version").string()=="0.2.0-control-candidate";
        catalogBinding();
        const auto classification=at(profile,"classification").string();
        if(classification!="synthetic_fixture"&&classification!=(candidate?"converted_candidate_reference":"accepted_contract_reference")) bad("SCHEMA_CLASSIFICATION","/profile/classification","Reference classification must match package schema");
        std::error_code ec; root=std::filesystem::canonical(input.sourceRoot,ec);
        if(ec||!std::filesystem::is_directory(root)) bad("SOURCE_ROOT","/source_root","Explicit source root is not an accessible directory");
        for(auto k:{"schema_version","content_version","source_manifest_sha256","source_acceptance"}) compare(at(package,k),at(at(profile,"reference_package"),k),"/"+std::string(k),"PACKAGE_FIDELITY");
        guard([&]{authority();});
        indexEntities(registry,entities,"/registry",curriculum); indexEntities(at(profile,"reference_registry"),expectedEntities,"/profile/reference_registry"); identityGraph();
        if(curriculum)for(const auto& entry:entities) {
            const auto prior=baselineEntities.find(entry.first);
            if(prior!=baselineEntities.end())for(const auto key:{"kind","parent"})
                if(at(*prior->second,key)!=at(*entry.second,key))issue("IDENTITY_REASSIGNED","/registry/"+entry.first,"Previously allocated identity kind/parent may not change");
        }
        compare(at(registry,"rules"),at(at(profile,"reference_registry"),"rules"),"/registry/rules","IDENTITY_FIDELITY");
        sourcePassages();
        for(const auto& r:at(at(profile,"reference_package"),"records").array()) {
            if(!r.isObject()||!r.find("id")) bad("PROFILE_RECORD","/profile/reference_package/records","Expected record identity");
            const auto id=text(at(r,"id"),"/profile/reference_package/records/id"); if(!expectedRecords.emplace(id,&r).second) bad("PROFILE_DUPLICATE_ID","/profile/reference_package/records","Duplicate reference ID");
        }
        std::set<std::string> allEvents;
        for(const auto& r:at(package,"records").array()) guard([&] {
            recordShape(r,"/records",limits,candidate,curriculum); const auto id=at(r,"id").string();
            if(!records.emplace(id,&r).second) { issue("DUPLICATE_ID","/records/"+id,"Duplicate record identity",id); return; }
            const auto count=at(r,"events").array().size();
            if(count>limits.events-eventTotal) bad("EVENT_COUNT_LIMIT","/records","Aggregate event count exceeds limit"); eventTotal+=count;
            for(const auto& e:at(r,"events").array()) if(!allEvents.insert(at(e,"event_id").string()).second) issue("DUPLICATE_EVENT_ID","/events","Event identity is not unique",id,at(e,"event_id").string());
            projectRecord(r);
        },r.find("id")&&r.find("id")->isString()?r.find("id")->string():std::string{});
        coverage(keys(records),keys(expectedRecords),"/records");
        if(candidate) {
            std::set<std::string> registered;for(const auto& kv:entities)if(at(*kv.second,"kind").string()=="variant")registered.insert(kv.first);
            coverage(usedVariants,registered,"/variants");
            if(allocation.find("records")) coverage(keys(records),objectKeys(at(allocation,"records")),"/allocation/records");
        }
        coverage(objectKeys(at(profile,"event_sources")),allEvents,"/profile/event_sources");
    }
public:
    Validator(const Input& i,const Limits& l):input(i),limits(l){}
    Result run() {
        guard([&]{execute();});
        checkpoint();
        std::sort(issues.begin(),issues.end(),[](const J& a,const J& b){ return std::tie(at(a,"record").string(),at(a,"event").string(),at(a,"field").string(),at(a,"code").string(),at(a,"severity").string())<std::tie(at(b,"record").string(),at(b,"event").string(),at(b,"field").string(),at(b,"code").string(),at(b,"severity").string()); });
        for(auto& report:recordReports) {
            checkpoint();
            const auto id=at(report,"id").string();
            const auto& refs=at(at(report,"preserved_record"),"source_refs").array();
            for(const auto& i:issues) if(at(i,"severity").string()=="error") {
                const auto r=at(i,"record").string(); const auto source=at(i,"source").string();
                const bool relatedSource=!source.empty()&&std::any_of(refs.begin(),refs.end(),[&](const J& ref){return ref.string()==source;});
                if((r.empty()&&source.empty())||r==id||relatedSource) report.object()["valid_reference"]=false;
            }
        }
        for(auto& report:variantReports) {
            checkpoint();
            const auto id=at(report,"item_id").string();
            for(const auto& r:recordReports) if(at(r,"id").string()==id&&!at(r,"valid_reference").boolean()) {report.object()["valid_reference"]=false;report.object()["technically_renderable"]=false;}
        }
        for(auto& variant:result.variants) {checkpoint();for(const auto& report:variantReports) if(at(report,"variant_id").string()==variant.id&&!at(report,"valid_reference").boolean())variant.readiness.technicallyRenderable=false;}
        std::sort(variantReports.begin(),variantReports.end(),[](const J& a,const J& b){return at(a,"variant_id").string()<at(b,"variant_id").string();});
        std::sort(recordReports.begin(),recordReports.end(),[](const J& a,const J& b){return at(a,"id").string()<at(b,"id").string();});
        J::Array sourceAssets; for(const auto& a:assets) sourceAssets.push_back(a.second);
        std::sort(sourceAssets.begin(),sourceAssets.end(),[](const J& a,const J& b){return at(a,"path").string()<at(b,"path").string();});
        J::Object config{{"version","validator-limits.1"},{"json_bytes",J::fromInteger(static_cast<std::int64_t>(limits.json.bytes))},{"json_depth",J::fromInteger(static_cast<std::int64_t>(limits.json.depth))},{"string_bytes",J::fromInteger(static_cast<std::int64_t>(limits.json.stringBytes))},{"json_values",J::fromInteger(static_cast<std::int64_t>(limits.json.values))},{"number_bytes",J::fromInteger(static_cast<std::int64_t>(limits.json.numberBytes))},{"records",J::fromInteger(static_cast<std::int64_t>(limits.records))},{"events",J::fromInteger(static_cast<std::int64_t>(limits.events))},{"passages",J::fromInteger(static_cast<std::int64_t>(limits.sources))},{"entities",J::fromInteger(static_cast<std::int64_t>(limits.entities))},{"asset_bytes",J::fromInteger(static_cast<std::int64_t>(limits.assetBytes))},{"total_asset_bytes",J::fromInteger(static_cast<std::int64_t>(limits.totalAssetBytes))}};
        result.validReference=!failed&&!result.records.empty(); result.exitCode=result.validReference?2:1;
        const auto count=[](std::size_t n){return J::fromInteger(static_cast<std::int64_t>(n));};
        result.report=J::Object{{"validator_version","canonical-validator.1"},{"schema_version",package.find("schema_version")?at(package,"schema_version"):J{}},{"content_version",package.find("content_version")?at(package,"content_version"):J{}},{"source_manifest_sha256",package.find("source_manifest_sha256")?at(package,"source_manifest_sha256"):J{}},{"classification",profile.find("classification")?at(profile,"classification"):J{}},{"validator_source_sha256",FATHOM_CONTENT_SOURCE_ID},{"configuration",config},{"configuration_sha256",sha256(json::stringify(config))},{"package_sha256",sha256(input.package)},{"registry_sha256",sha256(input.registry)},{"profile_sha256",sha256(input.profile)},{"expected_profile_sha256",input.expectedProfileSha256},{"valid_reference",result.validReference},{"curriculum_playback_authorized",false},{"exit_code",J::fromInteger(result.exitCode)},{"review_status","Reference binding only; no human converted-curriculum acceptance or release admission"},{"coverage",J::Object{{"expected_records",count(expectedRecords.size())},{"observed_records",count(records.size())},{"expected_entities",count(expectedEntities.size())},{"observed_entities",count(entities.size())},{"expected_passages",profile.find("reference_package")&&at(profile,"reference_package").find("sources")&&at(at(profile,"reference_package"),"sources").isObject()?count(at(at(profile,"reference_package"),"sources").object().size()):count(0)},{"observed_passages",package.find("sources")&&at(package,"sources").isObject()?count(at(package,"sources").object().size()):count(0)},{"events",count(eventTotal)},{"variants",count(usedVariants.size())},{"variant_event_memberships",count(variantEventTotal)}}},{"source_assets",sourceAssets},{"archived_evidence",[&]{J::Array values;for(const auto& item:archivedEvidence)values.push_back(item.second);return J(values);}()},{"authority_artifacts",profile.find("authority_artifacts")?at(profile,"authority_artifacts"):J{}},{"resource_plan",profile.find("resource_plan")?at(profile,"resource_plan"):J{}},{"records",recordReports},{"variants",variantReports},{"issues",issues}};
        checkpoint();
        return std::move(result);
    }
};
} // namespace
void verifyArchivedEvidence(const Input& input,const std::string& path,const std::string& originalSha){
    if(input.installedRuntime&&input.installedRuntime->hasArchivedEvidence(path)){
        if(std::filesystem::canonical(input.sourceRoot)!=input.installedRuntime->packageRoot())throw std::runtime_error("Archived evidence package differs");
        input.installedRuntime->verifyArchivedEvidence(path,originalSha);return;
    }
    const auto bytes=readBounded(input.sourceRoot/path,32*1024*1024,input.canceled);
    if(sha256(bytes)!=originalSha)throw std::runtime_error("Original authority bytes differ");
}
Result validate(const Input& input,const Limits& limits) { return Validator(input,limits).run(); }
} // namespace fathom::content
