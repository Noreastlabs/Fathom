#include "content/SourceRealization.hpp"
#include "content/Canonical.hpp"
#include "content/StrictJson.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <numeric>
#include <set>
#include <stdexcept>

namespace fathom::content::realization {
namespace {
using json::Value;
constexpr const char* kOracleSha = "8abc59e35481b65cb5c51dd8d6900db636fb91d63db99a5f683b190c676ed4e3";
constexpr const char* kSourceSha = "19b3b797b1fcccdc319a7bbc4ce35b910c690e700ecbdf91a2865dac98d5a65c";
constexpr const char* kOracleId = "L082-MA-S1-P1-bass-20260924";
constexpr const char* kOracleJson = R"FATHOM_ORACLE({"oracle_id":"L082-MA-S1-P1-bass-20260924","oracle_version":1,"review_refs":[{"asset":"independent-Level82-review","bytes":5207,"locator":"source/native gap verdict and original assertion","path":"Results/level-oracle/levels/level082/all105-r01/review-r01/review-results.md","sha256":"4608acb828f696c26ecadc07a9631cb84a161e6d0386fbe8d279b269190ceb19"},{"asset":"P119-correction-review","bytes":9988,"locator":"source reading and contract Correct","path":"Results/parallel-119/learner-realization-independent-review-r01/decision.md","sha256":"21958be0084f43c0126983a3f9ab6e9bc915f03719dade3dc7ff419b5498591c"}],"schema":"reviewed-source-oracle.1","source":{"assertion_basis":{"metric_slots":"derived from PDF actual page 3 Pass 1 bass quarter notes","pitch_role_order":"printed TXT lines 11-15 and PDF actual page 3","slot_end_is_acoustic_note_off":false},"events":[{"id":"bass-1","onset_q":[0,1],"pitch_class":0,"role":"bass","slot_end_q":[1,1],"spelling":"C"},{"id":"bass-2","onset_q":[1,1],"pitch_class":11,"role":"bass","slot_end_q":[2,1],"spelling":"B"},{"id":"bass-3","onset_q":[2,1],"pitch_class":9,"role":"bass","slot_end_q":[3,1],"spelling":"A"},{"id":"bass-4","onset_q":[3,1],"pitch_class":7,"role":"bass","slot_end_q":[4,1],"spelling":"G"}],"harmony_context":["Cmaj7","Cmaj7/B","Am7","G7"],"oracle_id":"L082-MA-S1-P1-bass-20260924","oracle_version":1,"schema":"source-constraint.1","scope":"Level82/ModuleA/Study1/Pass1/bass-only","source_refs":[{"asset":"TXT","bytes":7929,"locator":"lines 11-15","path":"Notes/music/guitar project/TXT version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.txt","sha256":"075685fca4a69a33860abfddddac2ec47ff744c245e4c474f8c8a9715f355318"},{"asset":"PDF","bytes":70289,"locator":"actual page 3; page 2 four-beat template","path":"Notes/music/guitar project/PDF version/Guitar_Exercises_Section_XI_Level_82_Walking_Bass_Chord_Melody_Chromatic_Approach_Bass_Lines_Bass_Substitutions_and_Solo_Guitar_Arrangements.pdf","sha256":"e12a87917b2a3537922e56e0139574627a59dbd7b4959073cfbf87a4a8846005"}],"source_unspecified":["octave","midi","string","fret","finger","tuning","capo","bpm","attack","timbre","acoustic_note_off","preview_gate"]}})FATHOM_ORACLE";
[[noreturn]] void fail(const char* code, const std::string& detail) { throw Error(code, detail); }
void require(bool ok, const char* code, const std::string& detail) { if (!ok) fail(code, detail); }
void asciiTree(const Value& v) {
    if (v.isString()) for (unsigned char c : v.string()) require(c >= 0x20 && c <= 0x7e, "NONASCII", "Printable ASCII string required");
    else if (v.isArray()) for (const auto& x : v.array()) asciiTree(x);
    else if (v.isObject()) for (const auto& [key,x] : v.object()) {
        for (unsigned char c : key) require(c >= 0x20 && c <= 0x7e, "NONASCII", "Printable ASCII key required");
        asciiTree(x);
    }
}
Value parseWire(const std::string& bytes) {
    require(bytes.size() <= 16384, "WIRE_SIZE", "Bounded Level82 wire exceeded");
    json::Limits limits; limits.bytes=16384; limits.depth=16; limits.stringBytes=2048; limits.values=512; limits.numberBytes=32;
    try { auto v=json::parse(bytes,limits); asciiTree(v); return v; }
    catch (const json::Error& e) { fail(e.code.c_str(), e.what()); }
}
const Value& field(const Value& v, const char* key) {
    require(v.isObject(), "SHAPE", "Expected object");
    const auto* found=v.find(key); require(found!=nullptr, "SHAPE", std::string("Missing ")+key); return *found;
}
void keys(const Value& v, std::initializer_list<const char*> expected) {
    require(v.isObject() && v.object().size()==expected.size(), "SHAPE", "Object key count");
    for (auto key : expected) require(v.find(key)!=nullptr, "SHAPE", std::string("Object key ")+key);
}
std::string str(const Value& v) { require(v.isString(), "TYPE", "Expected string"); return v.string(); }
std::int64_t integer(const Value& v) {
    std::int64_t out{};
    require(v.integer(out) && v.isNumber() && std::get<json::Number>(v.data).token==std::to_string(out), "INTEGER", "Shortest signed integer required");
    return out;
}
int bounded(const Value& v, int lo, int hi) {
    auto n=integer(v); require(n>=lo && n<=hi, "RANGE", "Integer outside supported range"); return static_cast<int>(n);
}
Rational rational(const Value& v, bool positive) {
    require(v.isArray() && v.array().size()==2, "RATIONAL", "Rational pair required");
    auto n=integer(v.array()[0]), d=integer(v.array()[1]);
    require(n >= (positive ? 1 : 0) && d>0 && std::gcd(n,d)==1, "RATIONAL", "Positive reduced rational required");
    return Rational{n,d};
}
Value number(std::int64_t n) { return Value::fromInteger(n); }
Value pair(const Rational& r) { return Value::Array{number(r.numerator()),number(r.denominator())}; }
const Value& oracleTree() {
    static const Value oracle=[] {
        const std::string bytes=kOracleJson;
        require(content::sha256(bytes)==kOracleSha, "ORACLE_FINGERPRINT", "Compiled oracle fingerprint drift");
        auto parsed=parseWire(bytes);
        require(json::stringify(parsed)==bytes, "ORACLE_CANONICAL", "Compiled oracle bytes are not canonical");
        keys(parsed,{"oracle_id","oracle_version","review_refs","schema","source"});
        require(str(field(parsed,"oracle_id"))==kOracleId && integer(field(parsed,"oracle_version"))==1 &&
                str(field(parsed,"schema"))=="reviewed-source-oracle.1", "ORACLE_ID", "Compiled oracle identity drift");
        return parsed;
    }();
    return oracle;
}
}
SourceOnly::SourceOnly(std::string oracleId, int oracleVersion, std::string oracleSha256, std::string sourceSha256)
    : oracleId_(std::move(oracleId)), oracleSha256_(std::move(oracleSha256)), sourceSha256_(std::move(sourceSha256)), oracleVersion_(oracleVersion) {}
DeclaredRealization::DeclaredRealization(SourceOnly verifiedSource, std::string state,
                                         std::string choiceSha, int bpm, int rate,
                                         std::string selectedMethod, music::Model projectedCandidate)
    : source(std::move(verifiedSource)), choiceState(std::move(state)), declaredSha256(std::move(choiceSha)),
      selectedBpm(bpm), sampleRateHz(rate), method(std::move(selectedMethod)), candidate(std::move(projectedCandidate)) {}
Error::Error(std::string c, const std::string& message) : std::runtime_error(message), code(std::move(c)) {}
const std::string& compiledOracleBytes() { static const std::string bytes=kOracleJson; return bytes; }
SourceOnly validateSource(const std::string& sourceJson) {
    const auto& trusted=field(oracleTree(),"source");
    auto parsed=parseWire(sourceJson);
    require(parsed==trusted, "SOURCE_ORACLE_MISMATCH", "Complete source assertion differs from compiled oracle");
    // Full tree equality validates every field; reconstruct solely from trusted assertions.
    const auto rebuilt=json::stringify(trusted);
    require(sourceJson==rebuilt, "NONCANONICAL_JSON", "Source bytes differ from reconstructed oracle assertions");
    require(content::sha256(rebuilt)==kSourceSha, "SOURCE_FINGERPRINT", "Source fingerprint drift");
    return {kOracleId,1,kOracleSha,kSourceSha};
}
DeclaredRealization validateDeclaredChoice(const SourceOnly& source, const std::string& choiceJson, const ActiveSetup& activeSetup) {
    (void)oracleTree();
    require(source.oracleId()==kOracleId && source.oracleVersion()==1 && source.oracleSha256()==kOracleSha && source.sourceSha256()==kSourceSha,
            "SOURCE_IDENTITY", "Unverified source-only identity");
    auto root=parseWire(choiceJson);
    keys(root,{"choice_state","events","method","oracle_sha256","sample_rate_hz","schema","selected_bpm","setup","source_sha256"});
    require(str(field(root,"schema"))=="declared-realization.1" && str(field(root,"choice_state"))=="declared-unconfirmed",
            "CHOICE_VERSION_STATE", "Unsupported version or confirmation claim");
    require(str(field(root,"oracle_sha256"))==source.oracleSha256() && str(field(root,"source_sha256"))==source.sourceSha256(),
            "CHOICE_IDENTITY", "Choice does not bind verified source and oracle");
    const auto& setup=field(root,"setup"); keys(setup,{"capo","fret_count","open_midi","schema"});
    require(str(field(setup,"schema"))=="guitar-setup.1", "SETUP_VERSION", "Unsupported setup version");
    const auto& opens=field(setup,"open_midi"); require(opens.isArray() && opens.array().size()==6, "SETUP_SHAPE", "Six strings required");
    std::array<int,6> tuning{}; for (std::size_t i=0;i<6;++i) tuning[i]=bounded(opens.array()[i],0,127);
    const std::array<int,6> standard{{40,45,50,55,59,64}};
    const int capo=bounded(field(setup,"capo"),0,12), fretCount=bounded(field(setup,"fret_count"),0,127);
    require(tuning==standard && fretCount==22, "SETUP_UNSUPPORTED", "Only standard six-string 22-fret setup supported");
    require(activeSetup.openMidi==tuning && activeSetup.capo==capo && activeSetup.fretCount==fretCount,
            "SETUP_ACTIVE_MISMATCH", "Declared and active setup differ");
    const int bpm=bounded(field(root,"selected_bpm"),20,300);
    const int rate=bounded(field(root,"sample_rate_hz"),0,192000);
    require(rate==44100 || rate==48000, "RATE_UNSUPPORTED", "Sample rate unsupported");
    const auto method=str(field(root,"method")); require(method=="picked-reference.1", "METHOD_UNSUPPORTED", "Method unsupported");
    const auto& rows=field(root,"events"); require(rows.isArray() && rows.array().size()==4, "EVENT_SHAPE", "Exactly four events required");
    const auto& oracleEvents=field(field(oracleTree(),"source"),"events").array();
    Value::Array rebuiltRows;
    music::Model model; model.itemId=std::string("declared:")+source.sourceSha256();
    model.schemaVersion="declared-realization.1"; model.contentVersion=source.oracleSha256();
    model.contentRevision=1; model.sourceRefs={source.oracleId(),source.sourceSha256()};
    model.instrument.openMidi.assign(tuning.begin(),tuning.end()); model.instrument.capo=capo;
    model.proposalExample=true; model.syntheticFixture=false;
    for (std::size_t i=0;i<4;++i) {
        const auto& row=rows.array()[i]; keys(row,{"fret","gate_q","midi","source_event","string"});
        const auto eventId=str(field(row,"source_event"));
        require(eventId==str(field(oracleEvents[i],"id")), "EVENT_ORDER", "Source event order differs");
        const int string=bounded(field(row,"string"),1,6), fret=bounded(field(row,"fret"),0,22), midi=bounded(field(row,"midi"),0,127);
        require(capo+fret<=fretCount, "CONTACT_RANGE", "Capo and relative fret exceed physical board");
        require(tuning[static_cast<std::size_t>(string-1)]+capo+fret==midi, "CONTACT_MIDI", "Contact does not sound declared MIDI");
        require(midi%12==integer(field(oracleEvents[i],"pitch_class")), "PITCH_CLASS", "Contact differs from authored pitch class");
        const auto gate=rational(field(row,"gate_q"),true);
        require(!(Rational{1}<gate), "GATE_SLOT", "Selected sounding gate exceeds one-quarter metric slot");
        rebuiltRows.emplace_back(Value::Object{{"fret",number(fret)},{"gate_q",pair(gate)},{"midi",number(midi)},
                                               {"source_event",eventId},{"string",number(string)}});
        music::Event event; event.id=eventId; event.sourceRef=source.oracleId();
        event.chordSymbol=str(field(field(oracleTree(),"source"),"harmony_context").array()[i]);
        event.kind=music::Kind::Contact; event.contact=music::Contact::Pitched;
        event.span={Rational{static_cast<std::int64_t>(i)},Rational{1}};
        music::Tone tone; tone.string=string; tone.fret=fret; tone.midi=midi;
        tone.spelling=str(field(oracleEvents[i],"spelling")); tone.attack=music::Attack::Picked;
        tone.soundingSpan=music::Span{Rational{static_cast<std::int64_t>(i)},gate};
        event.tones={tone}; model.events.push_back(std::move(event));
    }
    Value::Array rebuiltOpens; for (int midi:tuning) rebuiltOpens.emplace_back(number(midi));
    Value reconstructed=Value::Object{
        {"choice_state","declared-unconfirmed"},{"events",std::move(rebuiltRows)},{"method",method},
        {"oracle_sha256",source.oracleSha256()},{"sample_rate_hz",number(rate)},
        {"schema","declared-realization.1"},{"selected_bpm",number(bpm)},
        {"setup",Value::Object{{"capo",number(capo)},{"fret_count",number(fretCount)},
                               {"open_midi",std::move(rebuiltOpens)},{"schema","guitar-setup.1"}}},
        {"source_sha256",source.sourceSha256()}};
    require(choiceJson==json::stringify(reconstructed), "NONCANONICAL_JSON", "Choice bytes differ from validated reconstructed values");
    return DeclaredRealization{source,"declared-unconfirmed",content::sha256(choiceJson),bpm,rate,method,std::move(model)};
}
} // namespace fathom::content::realization
