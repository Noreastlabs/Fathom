#include "desktop/OriginalActivityRecovery.hpp"
#include "desktop/Appearance.hpp"
#include "fixtures/recovery/TestSupport.hpp"
#include "../Dependencies/SQLite-3.53.4/sqlite3.h"
#include <atomic>
#include <iostream>
using namespace recovery_test;
using Panel=fathom::desktop::OriginalActivityRecovery;
namespace {
int checks=0;
void ck(bool value,const char* message){++checks;std::cout<<(value?"PASS ":"FAIL ")<<message<<'\n';if(!value)throw std::runtime_error(message);}
void settle(Panel& panel){for(int i=0;i<5000&&panel.busy();++i){panel.poll();std::this_thread::sleep_for(std::chrono::milliseconds(1));}ck(!panel.busy(),"bounded recovery poll settles without blocking UI");}
fs::path privateDir(const fs::path& base,const char* name){auto p=base/name;ck(fs::create_directory(p),"new isolated case directory");fs::permissions(p,fs::perms::owner_all);return p;}
Value authority(ProfileStore& store){return at(required(store.snapshot(newUuid())).data,"authoritative");}
RecoveryBinding seed(ProfileStore& store,const Value& source,bool checkpoint=true){auto b=allocate(store,at(source,"context"),"Attempt");if(checkpoint){const auto q=snap(rebindCheckpoint(source,b.owner,b.context));required(store.checkpoint(newUuid(),b.owner,q.generation,q.sequence,q.bytes));}return b;}
void select(Panel& p,const RecoveryBinding& b){auto* combo=dynamic_cast<juce::ComboBox*>(p.findChildWithID("recovery-originals"));ck(combo&&combo->isEnabled(),"actual original selector enabled");int id=0;for(std::size_t i=0;i<p.originals().size();++i)if(p.originals()[i].binding.owner==b.owner)id=int(i)+1;ck(id!=0,"exact original offered by selector");combo->setSelectedId(id,juce::sendNotificationSync);settle(p);ck(p.selectedOriginal()&&p.selectedOriginal()->owner==b.owner,"selector callback keeps original owner");}
void render(Panel& p,const fs::path& path){p.setSize(920,680);p.setVisible(true);fathom::desktop::appearance::apply(p);auto image=p.createComponentSnapshot(p.getLocalBounds());juce::FileOutputStream out{juce::File(path.string())};ck(juce::PNGImageFormat().writeImageToStream(image,out),"actual recovery component render retained for assistant visual review");}
void firstAndMissing(const fs::path& root,const Value& cp){
 ProfileStore store(options(privateDir(root,"single")/"profile.sqlite"));auto b=seed(store,cp);auto before=authority(store);Panel panel;panel.setSize(920,680);
 ck(panel.attach(store),"attach read-only discovery");settle(panel);
 ck(panel.held()&&!panel.getPeer()&&panel.originals().size()==1&&!panel.selectedOriginal(),"single original is held but never automatically selected");ck(!panel.saveOriginal(),"Save before explicit owner selection refused");ck(authority(store)==before,"discovery preserves all fourteen authority tables");
 select(panel,b);render(panel,root/"selected-original.png");ck(!panel.selectOriginal(newUuid())&&panel.selectedOriginal()->owner==b.owner,"unknown selection cannot replace current original");
 const auto details=panel.recoveryDetails();ck(details.find(b.owner)!=std::string::npos&&details.find("Original context:")!=std::string::npos,"read-only support details name exact owner and context");
 ck(authority(store)==before,"selection and details preserve all authority");
 for(auto size:{juce::Point<int>{920,680},juce::Point<int>{1400,1000}}){panel.setSize(size.x,size.y);std::vector<juce::Component*> controls;for(auto* id:{"recovery-originals","recovery-details","recovery-save","recovery-check","recovery-keep","recovery-show-details","recovery-copy-details"}){auto* c=panel.findChildWithID(id);ck(c&&c->getWidth()>0&&c->getHeight()>0&&panel.getLocalBounds().contains(c->getBounds()),"recovery controls contained at supported geometry");controls.push_back(c);}for(std::size_t i=0;i<controls.size();++i)for(std::size_t j=0;j<i;++j)ck(!controls[i]->getBounds().intersects(controls[j]->getBounds()),"recovery controls do not overlap");}
 auto* keep=dynamic_cast<juce::TextButton*>(panel.findChildWithID("recovery-keep"));ck(keep&&keep->isEnabled(),"named Keep/details action available");keep->onClick();ck(panel.held()&&authority(store)==before,"Keep shows safe details without releasing debt or writing");
 ck(panel.saveOriginal(),"explicit original Save accepted");ck(!panel.saveOriginal()&&!panel.selectOriginal(newUuid()),"in-flight Save/selection cannot replace operation");settle(panel);ck(!panel.held(),"confirmed original save releases discovery hold");
 auto reply=required(store.recoveryState(newUuid(),b.owner));auto envelope=validateEnvelope(str(reply.data,"payload"));ck(envelope.owner==b.owner&&envelope.contextBytes==canonical(b.context)&&at(at(envelope.value,"result"),"active")==at(at(cp,"practice_snapshot"),"active"),"saved original owner/context/active facts exact");auto saved=authority(store);ck(!panel.saveOriginal()&&authority(store)==saved,"duplicate Save cannot change finalized authority");
 auto missing=seed(store,cp,false);before=authority(store);ck(panel.attach(store),"reattach missing-checkpoint discovery");settle(panel);select(panel,missing);ck(panel.held()&&!panel.saveOriginal()&&panel.recoveryDetails().find("No complete original checkpoint")!=std::string::npos,"missing checkpoint remains held with named support route, no invented outcome");render(panel,root/"missing-checkpoint.png");ck(panel.checkOriginal(),"explicit read-only missing-checkpoint check");settle(panel);ck(authority(store)==before,"missing-checkpoint check preserves exact all fourteen tables");
}
// Valid legacy/import-like multiple-original fixture, built only while both
// private Stores are closed. Never disable production allocation guards.
void mergeOriginal(const fs::path& target,const fs::path& other){
 sqlite3* db=nullptr;ck(sqlite3_open(target.c_str(),&db)==SQLITE_OK,"open own closed synthetic fixture");
 try{sqlite3_stmt* statement=nullptr;ck(sqlite3_prepare_v2(db,"ATTACH DATABASE ? AS other",-1,&statement,nullptr)==SQLITE_OK,"prepare bounded fixture attachment");sqlite3_bind_text(statement,1,other.c_str(),-1,SQLITE_TRANSIENT);const auto rc=sqlite3_step(statement);sqlite3_finalize(statement);ck(rc==SQLITE_DONE,"attach other isolated original");char* error=nullptr;const auto result=sqlite3_exec(db,"BEGIN; INSERT INTO session SELECT * FROM other.session; INSERT INTO identity SELECT * FROM other.identity; INSERT INTO checkpoint SELECT * FROM other.checkpoint; COMMIT; DETACH DATABASE other;",nullptr,nullptr,&error);std::string why=error?error:"";sqlite3_free(error);if(result!=SQLITE_OK)throw std::runtime_error(why);sqlite3_close(db);}catch(...){sqlite3_close(db);throw;}
}
void multiple(const fs::path& root,const Value& cp){
 auto dir=privateDir(root,"multiple"),other=privateDir(root,"other");RecoveryBinding a,b;
 {ProfileStore s(options(dir/"profile.sqlite"));a=seed(s,cp);}
 {ProfileStore s(options(other/"profile.sqlite"));b=seed(s,cp);}
 mergeOriginal(dir/"profile.sqlite",other/"profile.sqlite");ProfileStore store(options(dir/"profile.sqlite",false));auto before=authority(store);Panel panel;ck(panel.attach(store),"multiple-original discovery opens validated legacy fixture");settle(panel);ck(panel.originals().size()==2&&!panel.selectedOriginal()&&!panel.saveOriginal(),"multiple originals require explicit choice, no first-owner default");render(panel,root/"multiple-originals.png");ck(authority(store)==before,"listing multiple originals is read-only");
 select(panel,b);ck(panel.saveOriginal(),"selected second original can be recovered");settle(panel);ck(panel.held()&&panel.originals().size()==1&&!panel.selectedOriginal(),"remaining original stays held and unselected after first save");auto unchanged=required(store.recoveryState(newUuid(),a.owner));ck(str(unchanged.data,"state")=="checkpoint","saving selected owner never replaces other checkpoint");
 select(panel,a);ck(panel.saveOriginal(),"explicit remaining original Save");settle(panel);ck(!panel.held()&&at(authority(store),"finalized").array().size()==2,"two original owners each finalized once");
}
void uncertain(const fs::path& root,const Value& cp,const char* name,const std::string& phase,const std::string& suffix){
 auto dir=privateDir(root,name);std::atomic<bool> armed{false};int faults=0;std::vector<std::string> attempts;auto config=options(dir/"profile.sqlite");
 config.diagnosticHook=[&](const std::string& where,const std::string& op){if(where==phase&&op.size()>=suffix.size()&&op.compare(op.size()-suffix.size(),suffix.size(),suffix)==0){attempts.push_back(op);if(armed.exchange(false)){++faults;throw std::runtime_error("controlled original recovery acknowledgment/rollback fixture");}}};
 ProfileStore store(config);auto b=seed(store,cp);Panel panel;ck(panel.attach(store),"uncertain-case discovery");settle(panel);select(panel,b);armed=true;ck(panel.saveOriginal(),"original operation submitted once");const auto prefix=panel.recoveryOperationId();settle(panel);ck(faults==1&&panel.held()&&!prefix.empty()&&panel.recoveryOperationId()==prefix,"failed acknowledgment retains exact original operation identity and hold");
 ck(!panel.saveOriginal()&&!panel.selectOriginal(newUuid())&&!panel.attach(store),"uncertain outcome cannot be replaced by Save, selection, or reattach");auto* choice=dynamic_cast<juce::ComboBox*>(panel.findChildWithID("recovery-originals"));choice->setSelectedId(999,juce::sendNotificationSync);ck(choice->getSelectedId()==1&&panel.recoveryOperationId()==prefix,"stale selector callback cannot relabel the retained original");render(panel,dir/"uncertain-original.png");auto before=authority(store);for(int i=0;i<5;++i)panel.poll();ck(authority(store)==before&&faults==1,"poll does not retry or invent success");
 ck(panel.checkOriginal()&&panel.recoveryOperationId()==prefix,"explicit check retains original operation prefix");settle(panel);ck(!panel.held(),"explicit same-original reconciliation confirms recovery");auto r=required(store.recoveryState(newUuid(),b.owner));ck(str(r.data,"state")=="final"&&at(authority(store),"finalized").array().size()==1,"retry produces one immutable original final");for(const auto& op:attempts)ck(op==prefix+suffix,"write/ack retry never creates a replacement operation identity");
 if(phase=="after_commit"&&suffix==".commit")ck(authority(store)==before,"lost final ACK check makes no second write");
}
void conflict(const fs::path& root,const Value& cp){
 ProfileStore store(options(privateDir(root,"conflict")/"profile.sqlite"));auto b=seed(store,cp);Panel panel;ck(panel.attach(store),"conflict discovery");settle(panel);select(panel,b);auto preview=planRecovery(required(store.recoveryState(newUuid(),b.owner)),b);auto other=parseCanonical(preview.bytes);at(at(other,"result"),"assessment")="Easy";const auto bytes=canonical(other);required(store.seal(newUuid(),b.owner,bytes));required(store.commit(newUuid(),b.owner,bytes));auto before=authority(store);
 ck(panel.saveOriginal(),"original inspected outcome submitted for confirmation");settle(panel);ck(panel.held()&&!panel.checkOriginal()&&!panel.saveOriginal(),"conflicting durable outcome is held without overwrite retry");ck(panel.recoveryDetails().find("RECOVERY_CONFLICT")!=std::string::npos&&authority(store)==before,"conflict support details retain exact authority unchanged");render(panel,root/"conflicting-original.png");
}
}
int main(int argc,char** argv){try{
 if(argc!=3)throw std::runtime_error("Existing recovery evidence root and fresh private/tmp fixture required");const fs::path evidence=argv[1],dir=argv[2];
 if(!dir.is_absolute()||dir.parent_path()!=fs::path("/private/tmp")||fs::exists(dir)||fs::is_symlink(fs::symlink_status(dir)))throw std::runtime_error("Fresh private fixture required");fs::create_directory(dir);fs::permissions(dir,fs::perms::owner_all);
 juce::ScopedJuceInitialiser_GUI gui;auto cp=load(oracle(evidence,"running-partial")/"checkpoint.json");
 firstAndMissing(dir,cp);multiple(dir,cp);uncertain(dir,cp,"before-seal","before_commit",".seal");uncertain(dir,cp,"lost-seal-ack","after_commit",".seal");uncertain(dir,cp,"lost-commit-ack","after_commit",".commit");conflict(dir,cp);
 write(dir/"result.json",canonical(Object{{"checks",num(checks)},{"failures",num(0)},{"scope","Synthetic isolated SQLite/async worker and real recovery panel; no native peer, audio, human or acceptance claim"}}));std::cout<<"PASS "<<checks<<" focused named-original recovery checks\n";return 0;
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
