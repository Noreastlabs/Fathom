#include "metronome/MetronomePreferences.hpp"
#include "storage/ProfileStore.hpp"
#include "platform/ProfileAccessMac.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace fathom;using namespace fathom::metronome;using namespace fathom::storage;
namespace {
using V=json::Value;using O=V::Object;using A=V::Array;A checks;int failures=0;
void check(std::string name,bool pass){checks.push_back(O{{"case",name},{"passed",pass}});if(!pass)++failures;std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';}
template<class F>void rejects(const std::string& name,F f){bool rejected=false;try{f();}catch(const std::exception&){rejected=true;}check(name,rejected);}
Reply reply(const std::string& name,ProfileStore::Future f,Status status=Status::Confirmed){auto r=f.get();check(name,r.status==status);if(r.status!=status)std::cout<<"Observed "<<statusName(r.status)<<" "<<r.code<<" "<<r.message<<'\n';return r;}
std::string bytes(const Reply& r){return r.data.find("bytes")->string();}
V n(std::int64_t v){return V::fromInteger(v);}
}
int main(int argc,char** argv){
    try{
        if(argc!=3||!std::filesystem::path(argv[1]).is_absolute()||std::filesystem::exists(argv[1])||std::filesystem::exists(argv[2]))throw std::runtime_error("New absolute private profile directory and new result JSON required");
        const auto root=std::filesystem::path(argv[1]);std::filesystem::create_directory(root);std::filesystem::permissions(root,std::filesystem::perms::owner_all);StoreOptions options;options.path=root/"profile.sqlite";options.create=true;options.createdUtc="2026-09-08T05:00:00Z";options.preferenceValidator=preferenceValidator;
        Preferences p;auto id=newUuid();putPreset(p,id,"6/8 — 3+3",p.lastUsed,false);auto settings=p.lastUsed;settings.numerator=6;settings.denominator=8;settings.styles={Style::Accent,Style::Normal,Style::Normal,Style::Accent,Style::Normal,Style::Normal};settings.unit=scheduler::BeatUnit::DottedQuarter;settings.ramp=Ramp{true,5,2,90};putPreset(p,id,"6/8 — 3+3",settings,true);putPreset(p,newUuid(),"6/8 — 3+3",Settings{},false);p.lastUsed=settings;
        check("duplicate names permitted with distinct storageUUIDs",p.presets.size()==2&&p.presets[0].name==p.presets[1].name&&p.presets[0].id!=p.presets[1].id);rejects("duplicate ID requires explicit Replace",[&]{putPreset(p,id,"same",Settings{},false);});rejects("replacement must identify existing preset",[&]{putPreset(p,newUuid(),"missing",Settings{},true);});check("replacement retains exact ID and intended setting",p.presets[0].id==id&&p.presets[0].settings.numerator==6);
        auto original=canonical(encodePreferences(p));auto restored=decodePreferences(parseCanonical(original));check("exact full setting roundtrip",canonical(encodePreferences(restored))==original);check("stopped restore returns chosen exactsetting only",encodeSettings(restorePreset(restored,id,true))==encodeSettings(settings)&&encodeSettings(restoreLastUsed(restored,true))==encodeSettings(settings));rejects("active/unresolved restore refused",[&]{restorePreset(restored,id,false);});rejects("active/unresolved LastUsed refused",[&]{restoreLastUsed(restored,false);});rejects("unknown preset no fallback",[&]{restorePreset(restored,newUuid(),true);});
        Preferences limits;for(int i=0;i<32;++i)putPreset(limits,newUuid(),"duplicate name",Settings{},false);rejects("33rd preset refused",[&]{putPreset(limits,newUuid(),"overflow",Settings{},false);});auto replaceId=limits.presets[0].id;putPreset(limits,replaceId,"replacement",Settings{},true);check("explicit replace allowed at32",limits.presets.size()==32&&limits.presets[0].name=="replacement");
        std::string emoji;for(int i=0;i<64;++i)emoji+="🎸";Preferences unicode;putPreset(unicode,newUuid(),emoji,Settings{},false);check("64 multibyte Unicode scalars accepted",unicode.presets.size()==1);rejects("65 Unicode scalars refused",[&]{putPreset(unicode,newUuid(),emoji+"a",Settings{},false);});rejects("empty preset name refused",[&]{putPreset(unicode,newUuid(),"",Settings{},false);});rejects("invalid UTF8 refuses without replacement",[&]{putPreset(unicode,unicode.presets[0].id,std::string("\xed\xa0\x80",3),Settings{},true);});check("failed replacement preserves original",unicode.presets[0].name==emoji);
        auto invalid=encodePreferences(p);invalid.object()["version"]="future";check("unknown valueversion refused by semantic owner",!preferenceValidator("freeplay_timing",1,invalid));check("unknown namespace/version refused",!preferenceValidator("unrelated",1,encodePreferences(p))&&!preferenceValidator("freeplay_timing",2,encodePreferences(p)));invalid=encodePreferences(p);invalid.object()["running"]=true;rejects("preference cannot contain running state",[&]{decodePreferences(invalid);});invalid=encodePreferences(p);invalid.object()["presets"].array()[0].object()["version"]=n(2);rejects("unknown preset version not converted",[&]{decodePreferences(invalid);});invalid=encodePreferences(p);invalid.object()["presets"].array()[1].object()["id"]=id;rejects("duplicate stored preset IDs refused",[&]{decodePreferences(invalid);});
        std::string beforeHash;
        {
            ProfileStore store(options);reply("actual stopped freeplay preference CAS",store.compareExchangePreferences(newUuid(),"freeplay_timing",1,0,original,true));auto read=reply("read current semantic preference",store.readPreferences(newUuid(),"freeplay_timing"));check("exactBLOB and applicabletrue",bytes(read)==original&&read.data.find("applicable")->boolean());
            reply("stale revision refuses overwrite",store.compareExchangePreferences(newUuid(),"freeplay_timing",1,0,original,true),Status::Conflict);reply("running preference write refuses",store.compareExchangePreferences(newUuid(),"freeplay_timing",1,1,original,false),Status::DefiniteFailure);
            auto lesson=Preferences{};auto lessonBytes=canonical(encodePreferences(lesson));reply("independent lesson namespace",store.compareExchangePreferences(newUuid(),"lesson_timing",1,0,lessonBytes,true));check("lesson retains distinct default settings",bytes(reply("read lesson preferences",store.readPreferences(newUuid(),"lesson_timing")))==lessonBytes);check("freeplay unchanged by lesson save",bytes(reply("read freeplay after lesson save",store.readPreferences(newUuid(),"freeplay_timing")))==original);
            reply("unsupported preference cannot overwrite original",store.compareExchangePreferences(newUuid(),"freeplay_timing",1,1,canonical(invalid),true),Status::Unsupported);beforeHash=reply("snapshot before normal reopen",store.snapshot(newUuid())).data.find("snapshot_sha256")->string();
        }
        options.create=false;
        {
            ProfileStore reopened(options);check("normal reopen exact history/settings snapshot",reply("normal reopen snapshot",reopened.snapshot(newUuid())).data.find("snapshot_sha256")->string()==beforeHash);auto read=reply("normal reopen current preference",reopened.readPreferences(newUuid(),"freeplay_timing"));check("normal reopen exact stopped restoration",bytes(read)==original&&encodeSettings(restoreLastUsed(decodePreferences(parseCanonical(bytes(read))),true))==encodeSettings(settings));
        }
        // Older application without this semantic owner preserves bytes but cannot apply.
        options.preferenceValidator={};
        {ProfileStore older(options);auto read=reply("unknown handler read is available",older.readPreferences(newUuid(),"freeplay_timing"));check("unknown semantics preserved/applicablefalse",bytes(read)==original&&!read.data.find("applicable")->boolean());}
        // Future-shaped value is seeded using an explicit diagnostic semantic owner
        // in this isolated profile; production handler must preserve/refuse it.
        auto future=encodePreferences(p);future.object()["version"]="timing-future-synthetic";auto futureBytes=canonical(future);options.path=root/"future"/"profile.sqlite";options.create=true;options.preferenceValidator=[](const auto& key,auto version,const auto&){return key=="freeplay_timing"&&version==2;};
        {ProfileStore seed(options);reply("seed explicitly synthetic future value",seed.compareExchangePreferences(newUuid(),"freeplay_timing",2,0,futureBytes,true));}
        options.create=false;options.preferenceValidator=preferenceValidator;
        {ProfileStore current(options);auto read=reply("future preference preserved on current open",current.readPreferences(newUuid(),"freeplay_timing"));check("future bytes remain exact but inapplicable",bytes(read)==futureBytes&&!read.data.find("applicable")->boolean());rejects("future version cannot restore to fabricated default",[&]{decodePreferences(parseCanonical(bytes(read)));});}
        std::ofstream out(argv[2]);out<<canonical(O{{"classification","isolated synthetic preferences and normal reopen; no crash/native/human claim"},{"checks",checks},{"failures",n(failures)},{"original_preferences",parseCanonical(original)},{"snapshot_before_reopen_sha256",beforeHash}})<<'\n';if(!out)throw std::runtime_error("Cannot write evidence");return failures?1:0;
    }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
