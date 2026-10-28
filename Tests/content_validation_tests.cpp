#include "content/Canonical.hpp"
#include "fixtures/control_model_examples.hpp"
#include <algorithm>
#include <chrono>
#include <functional>
#include <fstream>
#include <iostream>
#include <limits>

using J=fathom::json::Value;
using namespace fathom;
namespace {
int checks=0,failures=0;
void expect(bool pass,const std::string& label) {++checks; if(!pass)++failures;std::cout<<(pass?"PASS ":"FAIL ")<<label<<'\n';}
J& field(J& v,const std::string& k) {return v.object().at(k);}
const J& field(const J& v,const std::string& k) {return v.object().at(k);}
J n(std::int64_t x) {return J::fromInteger(x);}
bool has(const content::Result& r,const std::string& code,const std::string& path="") {
    for(const auto& i:field(r.report,"issues").array()) if(field(i,"code").string()==code && field(i,"field").string().find(path)!=std::string::npos)return true;
    return false;
}
void parseBad(const std::string& s,const std::string& code,const json::Limits& limits={}) {
    try {json::parse(s,limits);expect(false,"parser rejects "+code);}
    catch(const json::Error& e) {expect(e.code==code,"parser "+code+" actual="+e.code);}
}
} // namespace
int main() {
    parseBad("{\"x\":1,\"\\u0078\":2}","JSON_DUPLICATE_KEY");
    parseBad("[NaN]","JSON_SYNTAX");parseBad("1e309","JSON_NONFINITE");parseBad("01","JSON_NUMBER");parseBad("1.","JSON_NUMBER");parseBad("1e","JSON_NUMBER");parseBad("true false","JSON_TRAILING");parseBad("[1,]","JSON_SYNTAX");
    parseBad("\"\\uD800\"","JSON_SURROGATE");parseBad("\"\\uDC00\"","JSON_SURROGATE");parseBad(std::string("\"\xc0\xaf\"",4),"JSON_UTF8");parseBad(std::string("\"\xed\xa0\x80\"",5),"JSON_UTF8");parseBad(std::string("\"\xf4\x90\x80\x80\"",6),"JSON_UTF8");
    expect(json::parse("\"\\uD834\\uDD1E\"").string()=="\xf0\x9d\x84\x9e","valid surrogate pair");
    std::int64_t i=0;expect(json::parse("9007199254740993").integer(i)&&i==9007199254740993LL,"integer preserved beyond2^53");expect(!json::parse("9223372036854775808").integer(i),"overflow integer not narrowed");expect(!json::parse("1.0").integer(i),"decimal token not integer");expect(!json::parse("true").integer(i),"boolean not integer");
    auto nul=json::parse("\"a\\u0000b\"");expect(nul.string().size()==3&&json::parse(json::stringify(nul))==nul,"NUL preserved in value");
    json::Limits l;l.bytes=3;expect(json::parse("[0]",l).isArray(),"byte limit boundary");parseBad("[00]","JSON_BYTE_LIMIT",l);
    l={};l.depth=1;expect(json::parse("[0]",l).isArray(),"depth boundary");parseBad("[[0]]","JSON_DEPTH_LIMIT",l);
    l={};l.stringBytes=2;expect(json::parse("\"ab\"",l).string()=="ab","string boundary");parseBad("\"abc\"","JSON_STRING_LIMIT",l);
    l={};l.values=2;expect(json::parse("[0]",l).isArray(),"value boundary");parseBad("[0,0]","JSON_VALUE_LIMIT",l);
    l={};l.numberBytes=2;expect(json::parse("10",l).isNumber(),"number boundary");parseBad("100","JSON_NUMBER_LIMIT",l);
    for(const auto& token: {"0","-0","-9223372036854775808","9223372036854775807","9007199254740993"}) {
        const auto value=json::parse(token);std::int64_t exact=0;
        expect(value.integer(exact)&&json::stringify(value)==token,"finite integer retains exact token "+std::string(token));
    }
    for(const auto& token: {"9223372036854775808","-9223372036854775809","1.0","-0.0","1e0","1E+0","1e-0","1e308"}) {
        const auto value=json::parse(token);std::int64_t exact=0;
        expect(!value.integer(exact)&&json::stringify(value)==token,"fallback retains full non-int64 token "+std::string(token));
    }
    for(const auto& rejected: std::vector<std::pair<std::string,std::pair<std::string,std::size_t>>>{
            {"1e309",{"JSON_NONFINITE",5}},{"-1e309",{"JSON_NONFINITE",6}},
            {"1.0x",{"JSON_TRAILING",3}},{"1e+",{"JSON_NUMBER",3}}}) {
        try {json::parse(rejected.first);expect(false,"number refusal and offset "+rejected.first);}
        catch(const json::Error& e) {expect(e.code==rejected.second.first&&e.offset==rejected.second.second,"number refusal and offset "+rejected.first);}
    }
    const std::filesystem::path root=FATHOM_SOURCE_ROOT;
    try {content::readBounded(root,1024);expect(false,"directory input refused");} catch(const std::exception&) {expect(true,"directory input refused");}
    try {content::readBounded("/dev/zero",1024);expect(false,"device input refused");} catch(const std::exception&) {expect(true,"device input refused");}
    auto read=[&](const std::string& f){return content::readBounded(root/"Tests/fixtures/canonical_controls"/f,32*1024*1024);};
    auto fixturePackage=json::parse(read("examples.json")),fixtureProfile=json::parse(read("expected-profile.json"));
    const auto profileBytes=json::stringify(fixtureProfile);
    content::Input input{json::stringify(fixturePackage),read("identity-registry.json"),profileBytes,content::sha256(profileBytes),root};
    auto package=json::parse(input.package),registry=json::parse(input.registry),profile=json::parse(input.profile);
    auto base=content::validate(input);
    expect(base.validReference&&base.exitCode==2&&base.records.size()==13,"13accepted controls valid reference, no runtime admission");
    expect(field(field(fixtureProfile,"authority_artifacts").array().front(),"path").string().rfind("Results/primary/",0)!=0,
           "historical authority path validates through read-only relocation fallback");
    if(!base.validReference)std::cout<<json::stringify(base.report)<<'\n';
    const auto refs=controlExamples();std::size_t events=0,tones=0;
    for(const auto& rr:base.records) {
        auto ref=std::find_if(refs.begin(),refs.end(),[&](const auto& m){return m.itemId==rr.id;});
        expect(ref!=refs.end(),rr.id+"stable reference identity"); if(ref==refs.end())continue;
        const auto& m=rr.source;expect(json::parse(m.preservedRecordJson)==json::parse(ref->preservedRecordJson),rr.id+"full original record preserved");
        expect(m.instrument.openMidi==ref->instrument.openMidi&&m.instrument.capo==ref->instrument.capo&&m.sourceRefs==ref->sourceRefs,rr.id+"instrument/source refs");
        expect(m.events.size()==ref->events.size(),rr.id+"event count");
        for(std::size_t k=0;k<std::min(m.events.size(),ref->events.size());++k) {
            const auto& a=m.events[k];const auto& b=ref->events[k];++events;tones+=a.tones.size();
            expect(a.id==b.id&&a.kind==b.kind&&a.span==b.span&&a.sourceRef==b.sourceRef&&a.chordSymbol==b.chordSymbol&&a.contact==b.contact&&a.handDirection==b.handDirection&&a.scopeStrings==b.scopeStrings&&a.tones.size()==b.tones.size(),a.id+"source/time/contact identity");
            for(std::size_t t=0;t<std::min(a.tones.size(),b.tones.size());++t) {
                const auto& x=a.tones[t];const auto& y=b.tones[t];
                bool same=x.string==y.string&&x.fret==y.fret&&x.midi==y.midi&&x.finger==y.finger&&x.spelling==y.spelling&&x.attack==y.attack&&x.tieFrom==y.tieFrom&&x.authoredTechnique==y.authoredTechnique&&x.memberSpan==y.memberSpan&&x.soundingSpan==y.soundingSpan&&x.degrees.size()==y.degrees.size();
                for(std::size_t d=0;d<std::min(x.degrees.size(),y.degrees.size());++d) {const auto& u=x.degrees[d];const auto& v=y.degrees[d];same=same&&u.context==v.context&&u.sourceLabel==v.sourceLabel&&u.rootPitchClass==v.rootPitchClass&&u.ordinal==v.ordinal&&u.alteration==v.alteration&&u.rootMidi==v.rootMidi;}
                expect(same,a.id+"tone/degree/finger/attack/gate "+std::to_string(t));
            }
        }
        expect(!rr.readiness.curriculumPlaybackAuthorized,rr.id+"not admitted");
    }
    expect(events==69&&tones==59,"69events/59tones exact");
    expect(has(base,"MODEL_unresolved_time")&&has(base,"MODEL_unresolved_binding")&&has(base,"MODEL_unresolved_scope")&&has(base,"MODEL_no_events"),"honest unresolved diagnostics");
    expect(json::stringify(base.report)==json::stringify(content::validate(input).report),"report deterministic");
    auto mutated=[&](const std::string& label,const std::function<void(J&,J&,J&)>& change,const std::string& code,const std::string& path="",bool synthetic=false) {
        auto p=package,g=registry,f=profile;change(p,g,f);
        if(synthetic) {field(f,"classification")="synthetic_fixture";field(f,"reference_package")=p;field(f,"reference_registry")=g;}
        content::Input in{json::stringify(p),json::stringify(g),json::stringify(f),content::sha256(json::stringify(f)),root};
        const auto r=content::validate(in);expect(!r.validReference&&r.exitCode==1&&has(r,code,path),label+" -> "+code+path);
        if(r.validReference||!has(r,code,path))std::cout<<json::stringify(r.report)<<'\n';
    };
    const auto scratch=std::filesystem::canonical(std::filesystem::temp_directory_path())/
        ("fathom-canonical-source-tests-"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    if(!std::filesystem::create_directory(scratch))throw std::runtime_error("Fresh owned Canonical test scratch required");
    std::filesystem::create_directories(scratch/"Results/primary/p06");
    std::filesystem::create_directories(scratch/"Results/p06");
    std::ofstream(scratch/"Results/primary/p06/one",std::ios::binary)<<"alias bytes";
    std::ofstream(scratch/"Results/p06/one",std::ios::binary)<<"exact bytes";
    std::ofstream(scratch/"Results/primary/p06/drift",std::ios::binary)<<"alias bytes";
    std::filesystem::create_symlink(root/"Results/primary/20260906124133Z-2.1.1.1.1-r01-evidence/identity-manifest.json",
                                    scratch/"Results/primary/p06/escape");
    std::filesystem::create_symlink(root/"Results/primary/20260906124133Z-2.1.1.1.1-r01-evidence/identity-manifest.json",
                                    scratch/"Results/p06/direct-escape");
    auto authorityProbe=[&](const std::string& path,const std::string& expected){
        auto p=package,pr=profile;
        field(p,"source_manifest_sha256")=expected;
        field(pr,"reference_package")=p;
        auto& first=field(pr,"authority_artifacts").array().front();
        field(first,"path")=path;field(first,"sha256")=expected;
        const auto pb=json::stringify(pr);
        return content::validate({json::stringify(p),input.registry,pb,content::sha256(pb),scratch});
    };
    expect(has(authorityProbe("Results/p06/one",content::sha256("alias bytes")),"SOURCE_HASH"),
           "existing historical path wins over primary alias");
    expect(has(authorityProbe("Results/p06/drift",std::string(64,'0')),"SOURCE_HASH"),
           "relocated alias still requires expected SHA-256");
    expect(has(authorityProbe("Results/p06/absent",content::sha256("alias bytes")),"SOURCE_READ"),
           "absent historical path and alias rejected");
    expect(has(authorityProbe("Results/../escape",content::sha256("alias bytes")),"SOURCE_PATH"),
           "historical path traversal rejected before fallback");
    expect(has(authorityProbe("Results/p06/escape",content::sha256("alias bytes")),"SOURCE_ESCAPE"),
           "relocated alias symlink escape rejected");
    expect(has(authorityProbe("Results/p06/direct-escape",content::sha256("alias bytes")),"SOURCE_ESCAPE"),
           "existing symlink escape never falls back");
    std::filesystem::remove_all(scratch);
    auto record=[](J& p,int level)->J& {for(auto& r:field(p,"records").array()){std::int64_t n=0;field(r,"legacy_level").integer(n);if(n==level)return r;}throw std::runtime_error("fixture level missing");};
    auto firstEvent=[&](J& p,int level)->J& {return field(record(p,level),"events").array()[0];};
    mutated("unused degree root still typed",[](auto&,auto&,auto& f){field(f,"degree_roots").object()["unused"]=false;},"TYPE_OBJECT","degree_roots");
    mutated("common cycle cannot be zero",[&](auto& p,auto&,auto&){field(field(field(record(p,74),"timing"),"phrases").array()[0],"common_cycle_q")=J::Array{n(0),n(1)};},"PHRASE_ZERO_SPAN","",true);
    mutated("declared cycles fit whole phrase",[&](auto& p,auto&,auto&){field(field(field(record(p,74),"timing"),"phrases").array()[0],"cycles")=n(3);},"PHRASE_CYCLE_BOUNDS","",true);
    mutated("return is fourth beat not new cycle",[&](auto& p,auto&,auto&){field(field(field(record(p,74),"timing"),"phrases").array()[1],"resolution_q")=J::Array{n(2),n(1)};},"PHRASE_RESOLUTION","",true);
    mutated("unknown schema",[](auto& p,auto&,auto&){field(p,"schema_version")="1";},"UNSUPPORTED_VALUE","schema_version");
    mutated("boolean revision",[&](auto& p,auto&,auto&){field(record(p,1),"content_revision")=true;},"TYPE_INTEGER","content_revision");
    mutated("missing context",[&](auto& p,auto&,auto&){record(p,1).object().erase("context");},"REQUIRED_FIELD","context");
    mutated("unknown instruction construct",[&](auto& p,auto&,auto&){field(record(p,1),"context").object()["autotranspose"]=true;},"UNKNOWN_FIELD","autotranspose");
    mutated("navigation extension refused",[](auto& p,auto&,auto&){p.object()["navigation"]=J::Object{};},"UNKNOWN_FIELD","navigation");
    mutated("duplicate record",[](auto& p,auto&,auto&){field(p,"records").array().push_back(field(p,"records").array()[0]);},"DUPLICATE_ID");
    mutated("missing record",[](auto& p,auto&,auto&){field(p,"records").array().erase(field(p,"records").array().begin());},"COVERAGE_MISSING","records");
    mutated("duplicate entity",[](auto&,auto& g,auto&){field(g,"entities").array().push_back(field(g,"entities").array()[0]);},"DUPLICATE_ID");
    mutated("dangling parent",[](auto&,auto& g,auto&){field(field(g,"entities").array()[1],"parent")="fg:course:absent";},"IDENTITY_DANGLING");
    mutated("parent cycle",[](auto&,auto& g,auto&){auto& e=field(g,"entities").array()[1];field(e,"parent")=field(e,"id");},"IDENTITY_CYCLE");
    mutated("wrong record parent",[&](auto& p,auto&,auto&){field(record(p,1),"module_id")="fg:module:000002";},"RECORD_PARENT");
    mutated("missing source passage",[](auto& p,auto&,auto&){field(p,"sources").object().erase("L1-TXT2-15");},"COVERAGE_MISSING","sources");
    mutated("undeclared source citation",[&](auto& p,auto&,auto&){field(record(p,1),"source_refs").array().clear();},"SOURCE_REFERENCE_UNDECLARED");
    mutated("event source binding absent",[](auto&,auto&,auto& f){field(f,"event_sources").object().erase("fg:item:000001:event:0001");},"EVENT_SOURCE_UNBOUND");
    mutated("event source wrong passage",[](auto&,auto&,auto& f){field(f,"event_sources").object()["fg:item:000001:event:0001"]="L83-PDF19";},"EVENT_SOURCE_UNDECLARED");
    mutated("source traversal",[](auto& p,auto&,auto&){field(field(p,"sources").object().begin()->second,"path")="../outside";},"SOURCE_PATH");
    mutated("source absolute path",[](auto& p,auto&,auto&){field(field(p,"sources").object().begin()->second,"path")="/etc/passwd";},"SOURCE_PATH");
    mutated("source byte hash",[](auto& p,auto&,auto&){field(field(p,"sources").object().begin()->second,"sha256")=std::string(64,'0');},"SOURCE_HASH");
    mutated("source text hash",[](auto& p,auto&,auto&){field(field(p,"sources").object().begin()->second,"text")="wrong";},"SOURCE_TEXT_HASH");
    mutated("source actual TXT span",[](auto& p,auto&,auto&){auto& s=field(p,"sources").object().at("L1-TXT2-15");field(s,"text")="wrong";field(s,"text_sha256")=content::sha256("wrong");},"SOURCE_TEXT_SPAN","text",true);
    mutated("source locator bound",[](auto& p,auto&,auto&){field(field(p,"sources").object().at("L1-TXT2-15"),"last_line")=n(9999999);},"SOURCE_LOCATOR");
    mutated("source manifest identity",[](auto& p,auto&,auto&){field(p,"source_manifest_sha256")=std::string(64,'0');},"AUTHORITY_BINDING");
    mutated("source acceptance identity",[](auto& p,auto&,auto&){field(p,"source_acceptance")="unseen.md";},"AUTHORITY_BINDING");
    mutated("wrong note pitch",[&](auto& p,auto&,auto&){field(firstEvent(p,1),"midi")=n(46);},"MODEL_pitch_position","",true);
    mutated("missing instrument string",[&](auto& p,auto&,auto&){field(firstEvent(p,1),"string")=n(7);},"MODEL_position","",true);
    mutated("negative fret",[&](auto& p,auto&,auto&){field(firstEvent(p,1),"fret")=n(-1);},"INTEGER_RANGE","fret",true);
    mutated("degree vs finger8",[&](auto& p,auto&,auto&){field(firstEvent(p,1),"finger")=n(8);},"INTEGER_RANGE","finger",true);
    mutated("open finger fretted",[&](auto& p,auto&,auto&){field(firstEvent(p,1),"finger")="O";},"MODEL_open_finger","",true);
    mutated("degree pitch contradiction",[&](auto& p,auto&,auto&){auto& d=field(firstEvent(p,12),"degree_contexts").object().at("A-major");field(d,"ordinal")=n(2);field(d,"source_label")="2";},"MODEL_degree_pitch","",true);
    mutated("degree label contradiction",[&](auto& p,auto&,auto&){field(field(firstEvent(p,12),"degree_contexts").object().at("A-major"),"source_label")="15";},"MODEL_degree_label","",true);
    mutated("empty event identity suffix",[&](auto& p,auto&,auto& f){auto& e=firstEvent(p,1);const auto old=field(e,"event_id").string();const std::string id="fg:item:000001:event:";field(e,"event_id")=id;auto binding=field(f,"event_sources").object().at(old);field(f,"event_sources").object().erase(old);field(f,"event_sources").object()[id]=binding;},"EVENT_IDENTITY","",true);
    mutated("duplicate event identity",[&](auto& p,auto&,auto&){auto& es=field(record(p,1),"events").array();field(es[1],"event_id")=field(es[0],"event_id");},"DUPLICATE_EVENT_ID");
    mutated("dangling tie",[&](auto& p,auto&,auto&){field(firstEvent(p,48),"attack")="held";field(firstEvent(p,48),"tie_from")="missing";},"MODEL_tie_identity","",true);
    mutated("repick with tie",[&](auto& p,auto&,auto&){for(auto& e:field(record(p,48),"events").array())if(e.find("tie_from")&&!field(e,"tie_from").null())field(e,"attack")="picked";},"MODEL_tie_identity","",true);
    mutated("zero duration",[&](auto& p,auto&,auto&){field(firstEvent(p,12),"duration_q")=J::Array{n(0),n(1)};},"MODEL_zero_duration","",true);
    mutated("unreduced rational",[&](auto& p,auto&,auto&){field(firstEvent(p,12),"duration_q")=J::Array{n(2),n(4)};},"RATIONAL_REDUCED","",true);
    mutated("invalid denominator",[&](auto& p,auto&,auto&){field(firstEvent(p,12),"duration_q")=J::Array{n(1),n(0)};},"INTEGER_RANGE","",true);
    mutated("pitched rest refused",[&](auto& p,auto&,auto&){for(auto& e:field(record(p,48),"events").array())if(field(e,"kind").string()=="rest"){e.object()["midi"]=n(60);break;}},"UNKNOWN_FIELD","midi",true);
    mutated("invented contact binding refused",[&](auto& p,auto&,auto&){field(firstEvent(p,58),"pitch_binding")=J::Object{};},"UNSUPPORTED_BINDING","",true);
    mutated("unknown contact operation",[&](auto& p,auto&,auto&){field(firstEvent(p,58),"contact")="silently_skip";},"UNSUPPORTED_VALUE","contact",true);
    mutated("muted contact requires scope",[&](auto& p,auto&,auto&){for(auto& e:field(record(p,58),"events").array())if(field(e,"contact").string()=="air"){field(e,"contact")="muted";break;}},"MUTED_SCOPE_REQUIRED","scope_strings");
    mutated("air not muted",[&](auto& p,auto&,auto&){for(auto& e:field(record(p,58),"events").array())if(field(e,"contact").string()=="air"){field(e,"contact")="muted";e.object()["scope_strings"]=J::Array{n(1)};break;}},"RECORD_FIDELITY","contact");
    mutated("chord member time",[&](auto& p,auto&,auto&){field(field(firstEvent(p,49),"members").array()[0],"onset_q")=J::Array{n(0),n(1)};},"MODEL_chord_time","",true);
    mutated("missing authored text reference",[&](auto& p,auto&,auto&){field(record(p,83),"authored_text_refs").array().pop_back();},"RECORD_FIDELITY","authored_text_refs");
    mutated("missing rubric anchor",[&](auto& p,auto&,auto&){field(field(field(record(p,83),"rubric"),"dimensions").array()[0],"anchors").array()[2]="generic clean";},"RECORD_FIDELITY","anchors");
    mutated("missing protected obligation",[&](auto& p,auto&,auto&){field(field(record(p,105),"rubric"),"required_obligations").array().pop_back();},"RECORD_FIDELITY","required_obligations");
    mutated("missing protected dimension",[&](auto& p,auto&,auto&){field(field(record(p,105),"rubric"),"protected_nonzero").array().pop_back();},"RECORD_FIDELITY","protected_nonzero");
    mutated("L97 days cannot replace unfamiliar excerpts",[&](auto& p,auto&,auto&){field(field(record(p,97),"rubric"),"repeatability")=J::Object{{"kind","two_separate_days"}};},"RECORD_FIDELITY","repeatability");
    mutated("L105 alternative only repeatability",[&](auto& p,auto&,auto&){field(field(field(record(p,105),"rubric"),"repeatability"),"alternative_affects")="all_obligations";},"UNSUPPORTED_VALUE","alternative_affects");
    mutated("L83 top not bass",[&](auto& p,auto&,auto&){field(field(field(record(p,83),"context"),"table").array()[5],"bass_inversion")="C#";},"UNAUTHORED_BASS");
    mutated("L83 A7 source table preserved",[&](auto& p,auto&,auto&){field(field(field(record(p,83),"context"),"table").array()[5],"chord_symbol")="Am7";},"RECORD_FIDELITY","chord_symbol");
    mutated("resource supplied false claim",[&](auto& p,auto&,auto&){field(field(record(p,97),"resource_requirements").array()[0],"supplied")=true;},"RESOURCE_UNSUPPLIED","supplied");
    mutated("automatic scorer refused",[&](auto& p,auto&,auto&){field(field(record(p,97),"rubric"),"evidence_kind")="automated_audio_score";},"UNSUPPORTED_VALUE","evidence_kind");
    mutated("runtime flag not authority",[&](auto& p,auto&,auto&){field(record(p,1),"runtime_eligible")=true;},"RUNTIME_NOT_ADMITTED","",true);
    {
        auto altered=package;field(field(field(record(altered,83),"rubric"),"dimensions").array()[0],"anchors").array()[2]="changed";
        auto in=input;in.package=json::stringify(altered);auto r=content::validate(in);
        const auto& rows=field(r.report,"records").array();auto row=std::find_if(rows.begin(),rows.end(),[](const J& x){return field(x,"id").string()=="fg:item:000011";});
        expect(!r.validReference&&row!=rows.end()&&!field(*row,"valid_reference").boolean()&&field(*row,"musical_valid_reference").boolean(),"record source fidelity failure distinct from valid eventless musical model");
    }
    {
        auto altered=package;field(altered,"source_manifest_sha256")=std::string(64,'0');auto in=input;in.package=json::stringify(altered);auto r=content::validate(in);
        expect(!r.validReference&&std::none_of(field(r.report,"records").array().begin(),field(r.report,"records").array().end(),[](const J& x){return field(x,"valid_reference").boolean();}),"global authority failure invalidates every record reference status");
    }
    auto wrong=input;wrong.profile+=" ";expect(has(content::validate(wrong),"PROFILE_HASH"),"external profile hash binds bytes independently");
    for(const auto& pair:std::vector<std::pair<std::string,std::function<void(content::Limits&)>>>{{"COLLECTION_LIMIT",[](auto& x){x.records=12;}},{"EVENT_COUNT_LIMIT",[](auto& x){x.events=68;}},{"SOURCE_COUNT_LIMIT",[](auto& x){x.sources=28;}},{"COLLECTION_LIMIT",[](auto& x){x.entities=39;}},{"SOURCE_ASSET_LIMIT",[](auto& x){x.assetBytes=1;}},{"SOURCE_TOTAL_LIMIT",[](auto& x){x.totalAssetBytes=1;}}}) {
        content::Limits bounds;pair.second(bounds);auto r=content::validate(input,bounds);expect(!r.validReference&&has(r,pair.first),"bounded refusal "+pair.first);
    }
    auto p=package,f=profile,g=registry;
    std::reverse(field(p,"records").array().begin(),field(p,"records").array().end());std::reverse(field(g,"entities").array().begin(),field(g,"entities").array().end());
    auto reordered=input;reordered.package=json::stringify(p);reordered.registry=json::stringify(g);expect(content::validate(reordered).validReference,"stable identity independent of record/entity order");
    p=package;f=profile;for(std::size_t k=0;k<field(record(p,1),"events").array().size();++k){auto& e=field(record(p,1),"events").array()[k];field(e,"onset_q")=J::Array{n(static_cast<std::int64_t>(k)),n(1)};field(e,"duration_q")=J::Array{n(1),n(1)};}
    field(f,"classification")="synthetic_fixture";field(f,"reference_package")=p;
    auto synth=input;synth.package=json::stringify(p);synth.profile=json::stringify(f);synth.expectedProfileSha256=content::sha256(synth.profile);auto sr=content::validate(synth);
    expect(sr.validReference&&sr.records[0].readiness.technicallyRenderable&&!sr.records[0].readiness.curriculumPlaybackAuthorized,"synthetic resolved notes renderable but never admitted");
    std::cout<<"CHECKS "<<checks<<" FAILURES "<<failures<<'\n';return failures?1:0;
}
