#include "content/SourceRealization.hpp"
#include "content/Canonical.hpp"
#include "content/StrictJson.hpp"
#include "core/ReferenceAudio.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <type_traits>

using namespace fathom;
using namespace fathom::content::realization;
using J=json::Value;
namespace {
int checks=0;
void expect(bool ok,const std::string& name) { ++checks; if(!ok) throw std::runtime_error(name); std::cout << "PASS " << name << '\n'; }
std::string read(const std::filesystem::path& p) {
    std::ifstream in(p,std::ios::binary); if(!in)throw std::runtime_error("Missing evidence: "+p.string());
    return {std::istreambuf_iterator<char>(in),std::istreambuf_iterator<char>()};
}
void pinned(const std::filesystem::path& root,const char* path,std::size_t size,const char* hash) {
    auto bytes=read(root/path);
    expect(bytes.size()==size && content::sha256(bytes)==hash,std::string("actual pinned bytes ")+path);
}
J& at(J& v,const std::string& key) { return v.object().at(key); }
const J& at(const J& v,const std::string& key) { return v.object().at(key); }
J num(std::int64_t n) { return J::fromInteger(n); }
template<class F> void refusal(F&& f,const std::string& name,const std::string& code="") {
    try { f(); } catch(const Error& e) { expect(code.empty() || e.code==code,name+" -> "+e.code); return; }
    catch(const json::Error& e) { expect(code.empty() || e.code==code,name+" -> "+e.code); return; }
    throw std::runtime_error("Accepted forbidden case: "+name);
}
template<class F> void sourceMutation(const std::string& bytes,F&& mutate,const std::string& name,const std::string& code="SOURCE_ORACLE_MISMATCH") {
    auto v=json::parse(bytes);mutate(v);refusal([&]{validateSource(json::stringify(v));},name,code);
}
template<class F> void choiceMutation(const SourceOnly& source,const std::string& bytes,F&& mutate,const std::string& name,const std::string& code="") {
    auto v=json::parse(bytes);mutate(v);refusal([&]{validateDeclaredChoice(source,json::stringify(v),{});},name,code);
}
bool issue(const content::Result& r,const std::string& code) {
    for(const auto& i:at(r.report,"issues").array()) if(at(i,"code").string()==code)return true;
    return false;
}
J& record(J& package,int level) {
    for(auto& r:at(package,"records").array()) {std::int64_t n=0;at(r,"legacy_level").integer(n);if(n==level)return r;}
    throw std::runtime_error("Missing control level");
}
void canonicalRegression(const std::filesystem::path& root) {
    const auto base=root/"Tests/fixtures/canonical_controls";
    auto p=json::parse(read(base/"examples.json")),g=json::parse(read(base/"identity-registry.json")),f=json::parse(read(base/"expected-profile.json"));
    at(f,"classification")="synthetic_fixture";
    auto check=[&](const J& changed,const std::string& expected,const std::string& label){
        auto profile=f;at(profile,"reference_package")=changed;at(profile,"reference_registry")=g;
        const auto bytes=json::stringify(profile);
        content::Input input{json::stringify(changed),json::stringify(g),bytes,content::sha256(bytes),root};
        auto result=content::validate(input);
        expect(!result.validReference && issue(result,expected),label);
    };
    auto bad=p;at(at(record(bad,1),"events").array().front(),"midi")=num(46);
    check(bad,"MODEL_pitch_position","historical Canonical wrong-note refusal");
    bad=p;at(at(record(bad,58),"events").array().front(),"contact")="silently_skip";
    check(bad,"UNSUPPORTED_VALUE","historical Canonical invalid-contact refusal");
}
}
int main() {
try {
    const std::filesystem::path root=FATHOM_SOURCE_ROOT;
    static_assert(!std::is_convertible_v<SourceOnly,music::Model>,"SourceOnly cannot become a concrete model");
    static_assert(!std::is_aggregate_v<DeclaredRealization>,"Validated realization cannot be aggregate forged");
    static_assert(!std::is_default_constructible_v<DeclaredRealization>,"Validated realization needs validator construction");
    static_assert(!std::is_constructible_v<DeclaredRealization,SourceOnly,std::string,std::string,int,int,std::string,music::Model>,
                  "P124 false-state/digest/model forgery must not construct");
    static_assert(std::is_copy_constructible_v<DeclaredRealization>,"Verified realization may be copied");
    pinned(root,"Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.txt",7929,"075685fca4a69a33860abfddddac2ec47ff744c245e4c474f8c8a9715f355318");
    pinned(root,"Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.pdf",70289,"e12a87917b2a3537922e56e0139574627a59dbd7b4959073cfbf87a4a8846005");
    pinned(root,"Results/level-oracle/levels/level082/all105-r01/review-r01/review-results.md",5207,"4608acb828f696c26ecadc07a9631cb84a161e6d0386fbe8d279b269190ceb19");
    pinned(root,"Results/parallel-119/learner-realization-independent-review-r01/decision.md",9988,"21958be0084f43c0126983a3f9ab6e9bc915f03719dade3dc7ff419b5498591c");
    const auto originalTxt=read(root/"Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.txt");
    expect(originalTxt.find("C-B-A-G")!=std::string::npos && originalTxt.find("Cmaj7/B")!=std::string::npos,"actual TXT has selected bass and harmony");
    const auto oracleBytes=compiledOracleBytes();
    expect(oracleBytes.size()==2271 && content::sha256(oracleBytes)=="8abc59e35481b65cb5c51dd8d6900db636fb91d63db99a5f683b190c676ed4e3","compiled oracle independent fingerprint");
    const auto oracle=json::parse(oracleBytes);
    expect(at(oracle,"review_refs").array().size()==2 && at(at(oracle,"source"),"events").array().size()==4,"compiled oracle review provenance and four-event scope");
    const auto& sourceTree=at(oracle,"source");
    for(const auto& ref:at(sourceTree,"source_refs").array()) {
        const auto bytes=read(root/at(ref,"path").string());
        std::int64_t count=0;at(ref,"bytes").integer(count);
        expect(bytes.size()==static_cast<std::size_t>(count) && content::sha256(bytes)==at(ref,"sha256").string(),
               "compiled source reference matches actual original bytes");
    }
    for(const auto& ref:at(oracle,"review_refs").array()) {
        const auto bytes=read(root/at(ref,"path").string());
        std::int64_t count=0;at(ref,"bytes").integer(count);
        expect(bytes.size()==static_cast<std::size_t>(count) && content::sha256(bytes)==at(ref,"sha256").string(),
               "compiled review reference matches actual review bytes");
    }
    const std::string names[] = {"C","B","A","G"}; const int classes[]={0,11,9,7};
    for(std::size_t i=0;i<4;++i){const auto& e=at(sourceTree,"events").array()[i];std::int64_t pc=0;at(e,"pitch_class").integer(pc);
        expect(at(e,"spelling").string()==names[i] && pc==classes[i] && at(e,"role").string()=="bass","compiled oracle event "+std::to_string(i+1));}
    expect(at(at(sourceTree,"assertion_basis"),"slot_end_is_acoustic_note_off").isBool() &&
           !at(at(sourceTree,"assertion_basis"),"slot_end_is_acoustic_note_off").boolean() &&
           at(sourceTree,"source_unspecified").array().size()==12,"derived slot and exact unspecified inventory");
    const auto fixture=root/"Build/parallel-118/learner-realization-contract-r02";
    auto sourceBytes=read(fixture/"source-contract.json"),aBytes=read(fixture/"declared-a.json"),bBytes=read(fixture/"declared-b.json");
    auto source=validateSource(sourceBytes);
    expect(source.sourceSha256()=="19b3b797b1fcccdc319a7bbc4ce35b910c690e700ecbdf91a2865dac98d5a65c" && source.oracleSha256()==content::sha256(oracleBytes),"source-only binds verified source/oracle identity");
    auto a=validateDeclaredChoice(source,aBytes,{}),b=validateDeclaredChoice(source,bBytes,{});
    expect(a.declaredSha256=="ab80ffbb1fa781311cbede284a08f75f07e70cd2490250f20a74d81beab64c71" &&
           b.declaredSha256=="97aa9003e8becab3305e9ed998994c53492bd8c25cf7c07689b829062ae01820" &&
           a.source.sourceSha256()==b.source.sourceSha256() && a.declaredSha256!=b.declaredSha256,"two distinct choices retain one source identity");
    for(const auto& d:{a,b}) {
        expect(d.choiceState=="declared-unconfirmed" && d.candidate.proposalExample && !d.candidate.syntheticFixture && d.candidate.events.size()==4,"declared candidate remains unconfirmed proposal");
        for(std::size_t i=0;i<4;++i) expect(d.candidate.events[i].kind==music::Kind::Contact && d.candidate.events[i].contact==music::Contact::Pitched &&
                d.candidate.events[i].span.duration==std::optional<Rational>{Rational{1}} && d.candidate.events[i].tones[0].soundingSpan.has_value(),"metric slot separate from selected sounding gate "+std::to_string(i));
        auto valid=music::validate(d.candidate);expect(valid.validReference(),"native music::validate declared contact projection");
        auto ready=music::assessReadiness(*valid.model,{{music::Attack::Picked},false,false,false});
        expect(ready.technicallyRenderable && !ready.curriculumPlaybackAuthorized,"technical readiness without Catalog admission");
        reference::Configuration config;config.owner.id[0]=6;config.owner.id[6]=0x40;config.owner.id[8]=0x80;config.owner.generation=1;config.owner.epoch=1;
        config.binding=82;config.sourceBinding=d.declaredSha256;config.rate=static_cast<std::uint32_t>(d.sampleRateHz);config.bpm=static_cast<std::uint16_t>(d.selectedBpm);config.cycle=Rational{4};config.method=reference::Method::Pluck;
        const auto program=reference::compile(valid.model,config);
        expect(program.voices().size()==4 && std::all_of(program.voices().begin(),program.voices().end(),[](const auto& v){return std::isfinite(v.hz) && v.hz>0;}),"finite ReferenceAudio technical compile");
    }
    sourceMutation(sourceBytes,[](auto& v){at(at(v,"source_refs").array()[1],"locator")="actual page 4";},"changed PDF locator");
    sourceMutation(sourceBytes,[](auto& v){at(at(v,"assertion_basis"),"pitch_role_order")="source-authored octave";},"altered authorship label");
    sourceMutation(sourceBytes,[](auto& v){at(v,"source_unspecified").array().erase(at(v,"source_unspecified").array().begin()+1);},"removed unspecified MIDI");
    sourceMutation(sourceBytes,[](auto& v){v.object()["fixed_tab"]="E3";},"forged source TAB");
    sourceMutation(sourceBytes,[](auto& v){at(at(v,"events").array()[0],"spelling")="D";},"changed authored pitch");
    sourceMutation(sourceBytes,[](auto& v){at(at(v,"events").array()[0],"slot_end_q")=J::Array{num(2),num(1)};},"changed derived slot");
    sourceMutation(sourceBytes,[](auto& v){at(v,"oracle_version")=num(2);},"stale source version");
    sourceMutation(sourceBytes,[](auto& v){at(v,"source_refs").array()[0].object()["extra"]=num(1);},"unknown nested source assertion");
    refusal([&]{validateSource(sourceBytes+"\n");},"source trailing newline","NONCANONICAL_JSON");
    refusal([&]{validateSource("{\"schema\":1,\"schema\":2}");},"duplicate source key","JSON_DUPLICATE_KEY");
    refusal([&]{validateDeclaredChoice(source,"{\"schema\":1,\"schema\":2}",{});},"duplicate choice key","JSON_DUPLICATE_KEY");
    static_assert(!std::is_default_constructible_v<SourceOnly>,"SourceOnly requires verified construction");
    choiceMutation(source,aBytes,[](auto& v){at(v,"choice_state")="learner-confirmed";},"false learner confirmation","CHOICE_VERSION_STATE");
    choiceMutation(source,aBytes,[](auto& v){v.object()["origin"]="agent-example";},"agent-example authorship");
    choiceMutation(source,aBytes,[](auto& v){at(v,"source_sha256")=std::string(64,'0');},"stale source hash","CHOICE_IDENTITY");
    choiceMutation(source,aBytes,[](auto& v){at(v,"oracle_sha256")=std::string(64,'0');},"forged oracle hash","CHOICE_IDENTITY");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"setup"),"capo")=num(1);},"active setup mismatch","SETUP_ACTIVE_MISMATCH");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"setup"),"open_midi").array()[0]=num(41);},"unsupported tuning","SETUP_UNSUPPORTED");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"setup"),"fret_count")=num(24);},"unsupported physical board","SETUP_UNSUPPORTED");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"midi")=num(49);},"contact/MIDI mismatch","CONTACT_MIDI");
    choiceMutation(source,aBytes,[](auto& v){auto& row=at(v,"events").array()[0];at(row,"string")=num(1);at(row,"fret")=num(7);at(row,"midi")=num(47);},"valid contact with wrong authored pitch class","PITCH_CLASS");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"string")=num(7);},"invalid string","RANGE");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"fret")=num(22);},"contact physical mismatch","CONTACT_MIDI");
    { auto v=json::parse(aBytes);at(at(v,"setup"),"capo")=num(1);at(at(v,"events").array()[0],"fret")=num(22);
      ActiveSetup selected;selected.capo=1;
      refusal([&]{validateDeclaredChoice(source,json::stringify(v),selected);},"capo plus fret exceeds physical board","CONTACT_RANGE"); }
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"gate_q")=J::Array{num(3),num(2)};},"overlong gate","GATE_SLOT");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"gate_q")=J::Array{num(0),num(1)};},"zero gate","RATIONAL");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"gate_q")=J::Array{num(2),num(2)};},"unreduced gate","RATIONAL");
    choiceMutation(source,aBytes,[](auto& v){at(at(v,"events").array()[0],"gate_q")=J::Array{num(1),num(-2)};},"negative denominator","RATIONAL");
    choiceMutation(source,aBytes,[](auto& v){at(v,"sample_rate_hz")=num(96000);},"unsupported rate","RATE_UNSUPPORTED");
    choiceMutation(source,aBytes,[](auto& v){at(v,"method")="sine";},"unsupported method","METHOD_UNSUPPORTED");
    choiceMutation(source,aBytes,[](auto& v){at(v,"selected_bpm")=num(301);},"unsupported BPM","RANGE");
    choiceMutation(source,aBytes,[](auto& v){at(v,"selected_bpm")=true;},"boolean BPM","INTEGER");
    choiceMutation(source,aBytes,[](auto& v){at(v,"selected_bpm")=json::Number{"80.0"};},"float BPM","INTEGER");
    choiceMutation(source,aBytes,[](auto& v){at(v,"selected_bpm")=json::Number{"-0"};},"nonshortest integer","INTEGER");
    choiceMutation(source,aBytes,[](auto& v){at(v,"events").array().pop_back();},"missing event","EVENT_SHAPE");
    choiceMutation(source,aBytes,[](auto& v){std::swap(at(v,"events").array()[0],at(v,"events").array()[1]);},"wrong event order","EVENT_ORDER");
    choiceMutation(source,aBytes,[](auto& v){at(v,"events").array()[0].object()["extra"]=num(1);},"unknown nested choice field","SHAPE");
    refusal([&]{validateDeclaredChoice(source,aBytes+" ",{});},"noncanonical whitespace","NONCANONICAL_JSON");
    auto escaped=aBytes;auto position=escaped.find("picked-reference.1");escaped.replace(position,1,"\\u0070");
    refusal([&]{validateDeclaredChoice(source,escaped,{});},"noncanonical equivalent escape","NONCANONICAL_JSON");
    choiceMutation(source,aBytes,[](auto& v){at(v,"method")="\xc3\xa9";},"non-ASCII method","NONASCII");
    canonicalRegression(root);
    std::cout << "PASS TOTAL " << checks << '\n';
} catch(const std::exception& e) { std::cerr << "FAIL " << e.what() << '\n'; return 1; }
return 0;
}
