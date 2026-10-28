#include "desktop/SetupPreferences.hpp"
#include "desktop/PresentationPreferences.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <thread>
using namespace fathom;namespace setup=fathom::desktop::setup;
int main(int argc,char**argv){int checks=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("fresh output directory required");std::filesystem::create_directory(argv[1]);std::filesystem::permissions(argv[1],std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);std::ofstream log(std::filesystem::path(argv[1])/"checks.tsv");
 auto ck=[&](bool b,const char*n){++checks;log<<n<<'\t'<<(b?"PASS":"FAIL")<<'\n';if(!b)throw std::runtime_error(n);};
 auto wait=[](storage::ProfileStore::Future f){if(f.wait_for(std::chrono::seconds(5))!=std::future_status::ready)throw std::runtime_error("original Store future timeout, no retry");return f.get();};
 auto settle=[](setup::PreferencesController&c){const auto end=std::chrono::steady_clock::now()+std::chrono::seconds(5);while(c.inFlight()){c.poll();if(std::chrono::steady_clock::now()>=end)throw std::runtime_error("original preference future timeout");std::this_thread::sleep_for(std::chrono::milliseconds(1));}};
 setup::Model defaults;auto old=setup::encodePreferences(defaults);old.object().erase("board_display");const auto oldBytes=storage::canonical(old);
 ck(old.object().size()==8&&setup::decodePreferences(old).boardDisplay==setup::BoardDisplay{},"exactlegacy8 defaultshiddenBasicSharp");
 for(auto mode:{setup::BoardMode::Basic,setup::BoardMode::Finger,setup::BoardMode::Note})for(auto spelling:{setup::NoteSpelling::Sharp,setup::NoteSpelling::Flat}){auto m=defaults;m.boardDisplay={true,mode,spelling};auto value=setup::encodePreferences(m);ck(value.object().size()==9&&setup::decodePreferences(value)==m,"new9 exactall6 displaycombinations roundtrip");ck(storage::canonical(value.object().at("guitar"))==storage::canonical(old.object().at("guitar")),"display choices preserve guitar5");}
 auto refuses=[&](json::Value v){return !setup::preferenceValidator(setup::preferenceKey,1,v);};
 auto invalid=setup::encodePreferences(defaults);invalid.object()["board_display"].object()["visible"]=json::Value::fromInteger(1);ck(refuses(invalid),"visible integer refused");
 invalid=setup::encodePreferences(defaults);invalid.object()["board_display"].object()["mode"]="guess-finger";ck(refuses(invalid),"unknown mode refused");
 invalid=setup::encodePreferences(defaults);invalid.object()["board_display"].object()["spelling"]="automatic";ck(refuses(invalid),"unknown spelling refused");
 invalid=setup::encodePreferences(defaults);invalid.object()["board_display"].object()["finger"]="1";ck(refuses(invalid),"invented finger preference refused");
 storage::StoreOptions opts;opts.path=std::filesystem::path(argv[1])/"profile.sqlite";opts.create=true;opts.createdUtc="2026-10-09T16:00:00Z";opts.preferenceValidator=desktop::presentation::composedPreferenceValidator;
 storage::ProfileStore store(opts);auto snap=wait(store.snapshot(storage::newUuid()));ck(snap.status==storage::Status::Confirmed,"synthetic Store snapshot");auto identity=snap.data.object().at("profile_id").string();
 ck(wait(store.compareExchangePreferences(storage::newUuid(),setup::preferenceKey,1,0,oldBytes,true)).status==storage::Status::Confirmed,"seed actuallegacy8 preference");
 setup::PreferencesController a,b;ck(a.attach(store,identity)&&b.attach(store,identity),"two controllers sameoriginalprofile");settle(a);settle(b);
 auto bytes=[&]{auto r=wait(store.readPreferences(storage::newUuid(),setup::preferenceKey));if(r.status!=storage::Status::Confirmed)throw std::runtime_error("preference absent");return r.data.object().at("bytes").string();};
 ck(bytes()==oldBytes&&!a.dirty()&&a.observedRevision()==1,"legacy read no migrationwrite");
 auto chosen=a.model();chosen.boardDisplay={true,setup::BoardMode::Note,setup::NoteSpelling::Flat};a.choose(chosen);ck(!a.save(false)&&bytes()==oldBytes&&a.dirty(),"running/unresolved save refuses retains draftandlegacybytes");
 ck(a.save(true),"explicit stoppedresolved save admitted");settle(a);const auto newBytes=bytes();ck(a.model()==chosen&&!a.dirty()&&a.observedRevision()==2&&newBytes==storage::canonical(setup::encodePreferences(chosen)),"oneCASsave produces exactnew9");
 ck(!a.save(true)&&bytes()==newBytes,"identical resolved choice no duplicatewrite");
 auto competing=b.model();competing.boardDisplay={true,setup::BoardMode::Finger,setup::NoteSpelling::Sharp};b.choose(competing);ck(b.save(true),"stalecontroller submits ownexpectedrevision");settle(b);ck(b.state()==setup::PreferenceState::Conflict&&bytes()==newBytes&&!b.save(true),"CASconflict no overwriteor automaticretry");
 setup::PreferencesController reopened;ck(reopened.attach(store,identity),"reopen sameprofile");settle(reopened);ck(reopened.model()==chosen&&!reopened.dirty()&&bytes()==newBytes,"persisted display restoreswithoutnewwrite");
 ck(guitar::tuning(guitar::Preset::OpenE)==std::array<int,6>{{40,47,52,56,59,64}},"OpenE genuineE-B-E-Gsharp-B-E pitches");
 std::cout<<"PASS "<<checks<<" board preference checks\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL after "<<checks<<": "<<e.what()<<'\n';return 1;}}
