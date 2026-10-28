#include "storage/ManualDraftStore.hpp"
#include "desktop/PresentationPreferences.hpp"
#include "tasks/ManualProcedureGraph.hpp"
#include "ManualProcedureGraphFixture.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
using namespace fathom;using namespace storage;namespace md=storage::manual_drafts;
int main(int argc,char** argv){int n=0;try{
 if(argc!=2||std::filesystem::exists(argv[1]))throw std::runtime_error("fresh disposable directory required");std::filesystem::create_directory(argv[1]);std::filesystem::permissions(argv[1],std::filesystem::perms::owner_all,std::filesystem::perm_options::replace);std::ofstream log(std::filesystem::path(argv[1])/"checks.tsv");auto ck=[&](bool b,const char* m){++n;log<<m<<'\t'<<(b?"PASS":"FAIL")<<std::endl;if(!b)throw std::runtime_error(m);};
 StoreOptions o;o.path=std::filesystem::path(argv[1])/"profile.sqlite";o.create=true;o.createdUtc="2026-10-24T22:00:00Z";o.preferenceValidator=desktop::presentation::composedPreferenceValidator;
 bool lose=false;std::string loseOperation;int writes=0;o.diagnosticHook=[&](const std::string& phase,const std::string& op){if(phase=="before_commit")++writes;if(lose&&phase=="after_commit"&&(loseOperation.empty()||op==loseOperation)){lose=false;throw std::runtime_error("controlled lost acknowledgment");}};
 auto store=std::make_unique<ProfileStore>(o);auto id=store->readProfileIdentity(newUuid()).get().data.object().at("profile_id").string();auto draft=newUuid();const std::string contract(64,'a');
 std::string payload;payload.resize(md::chunkBytes*2+37);for(std::size_t i=0;i<payload.size();++i)payload[i]=static_cast<char>(i%256);payload[md::chunkBytes+1]=static_cast<char>(17);
 auto p=md::Repository::prepare(id,draft,"source/test",contract,payload,7,0);
 ck(md::Repository::publish(*store,p,false).status==Status::Busy&&writes==0,"unresolved/running gate performs no write");
 ck(md::Repository::publish(*store,p,true).status==Status::Confirmed&&writes==4,"3 chunks before one manifest");
 auto r=md::Repository::load(*store,id,draft);ck(r.receipt.status==Status::Confirmed&&r.payload==payload&&r.revision==1&&r.watermark==7,"binary multichunk exact load");
 auto before=writes;ck(md::Repository::publish(*store,p,true).status==Status::Confirmed&&writes==before,"identical value confirmation no duplicate write");
 auto wrong=md::Repository::prepare(newUuid(),newUuid(),"source/test",contract,payload,7,0);ck(md::Repository::publish(*store,wrong,true).status==Status::Conflict&&writes==before,"wrong actual Store profile refuses before writes");
 auto stale=md::Repository::prepare(id,draft,"source/test",contract,"stale",8,0);ck(md::Repository::publish(*store,stale,true).status==Status::Conflict&&writes==before,"stale revision cannot replace published draft");
 auto second=md::Repository::prepare(id,newUuid(),"source/test",contract,payload,7,0);ck(md::Repository::publish(*store,second,true).status==Status::Confirmed&&writes==before+1,"identical content remains a distinct draft with reused immutable chunks");
 auto replacement=md::Repository::prepare(id,draft,"source/test",contract,payload+"new",8,1);lose=true;loseOperation=replacement.operationId();auto failed=md::Repository::publish(*store,replacement,true);ck(failed.status==Status::Unresolved&&replacement.unresolved(),"manifest after-commit acknowledgment loss retained");before=writes;
 ck(md::Repository::publish(*store,replacement,true).code=="DRAFT_RECONCILE_REQUIRED"&&writes==before,"unknown original publication cannot auto-retry");
 store.reset();o.create=false;store=std::make_unique<ProfileStore>(o);ck(md::Repository::reconcile(*store,replacement).status==Status::Confirmed&&!replacement.unresolved()&&writes==before,"same original publication reconciled by exact value after normal close/reopen");
 r=md::Repository::load(*store,id,draft);ck(r.payload==payload+"new"&&r.watermark==8&&r.revision==2,"reopened revision2 exact bytes and watermark");
 auto chunkLossDraft=newUuid();auto chunkLoss=md::Repository::prepare(id,chunkLossDraft,"source/test",contract,"brand-new chunk",9,0);loseOperation.clear();lose=true;ck(md::Repository::publish(*store,chunkLoss,true).status==Status::Unresolved,"chunk acknowledgment loss stops before manifest");
 ck(md::Repository::load(*store,id,chunkLossDraft).receipt.status==Status::DefinitelyAbsent,"partial chunks expose no draft as saved");
 store.reset();store=std::make_unique<ProfileStore>(o);ck(md::Repository::reconcile(*store,chunkLoss).status==Status::DefinitelyAbsent,"reopen confirms original manifest not published");before=writes;ck(md::Repository::publish(*store,chunkLoss,true).status==Status::Confirmed&&writes==before+1,"explicit original retry reuses exact committed chunk and writes manifest once");
 auto bad=storage::parseCanonical(p.manifestBytes());bad.object()["watermark"]=Value::fromInteger(-1);ck(!md::preferenceValidator(md::draftPrefix+draft,1,bad),"negative watermark rejected");
 bad=storage::parseCanonical(p.manifestBytes());bad.object()["chunks"].array().pop_back();ck(!md::preferenceValidator(md::draftPrefix+draft,1,bad),"incomplete chunk roster rejected");
 bad=storage::parseCanonical(p.manifestBytes());bad.object()["extra"]=true;ck(!md::preferenceValidator(md::draftPrefix+draft,1,bad),"unknown manifest field rejected");
 bad=Value::Object{{"format","manual-continuation-chunk-v1"},{"sha256",contract},{"hex","zz"}};ck(!md::preferenceValidator(md::chunkPrefix+contract,1,bad),"malformed chunk encoding refused");
 ck(!md::preferenceValidator(md::draftPrefix+draft,2,parseCanonical(p.manifestBytes())),"future namespace not interpreted");
 // Supported manifest with a missing content object is preserved, not repaired
 // or silently replaced with an empty/new continuation.
 auto missingDraft=newUuid();bad=storage::parseCanonical(p.manifestBytes());bad.object()["draft_id"]=missingDraft;bad.object()["chunks"].array()[0]=std::string(64,'b');auto missingBytes=canonical(bad);
 ck(store->compareExchangePreferences(newUuid(),md::draftPrefix+missingDraft,1,0,missingBytes,true).get().status==Status::Confirmed,"seed valid-shaped unavailable draft without body mutation");
 r=md::Repository::load(*store,id,missingDraft);ck(r.receipt.status==Status::Unsupported&&r.payload.empty()&&r.receipt.code=="DRAFT_PRESERVED_UNAVAILABLE","missing chunk refuses restore and exposes no partial payload");
 ck(store->readPreferences(newUuid(),md::draftPrefix+missingDraft).get().data.object().at("bytes").string()==missingBytes,"unavailable original manifest remains exact");
 auto a=md::Repository::prepare(id,draft,"source/test",contract,"winner",9,2),b=md::Repository::prepare(id,draft,"source/test",contract,"loser",10,2);ck(md::Repository::publish(*store,a,true).status==Status::Confirmed&&md::Repository::publish(*store,b,true).status==Status::Conflict,"two competing revision2 drafts have one winner");
 r=md::Repository::load(*store,id,draft);ck(r.payload=="winner"&&r.revision==3,"conflicting draft does not overwrite winner");
 ck(md::Repository::load(*store,newUuid(),draft).receipt.status==Status::Conflict,"load checks actual profile binding");
 // Loss during replacement chunks must leave the previous published owner.
 auto interrupted=md::Repository::prepare(id,draft,"source/test",contract,"replacement interrupted before manifest",11,3);loseOperation.clear();lose=true;
 ck(md::Repository::publish(*store,interrupted,true).status==Status::Unresolved,"replacement chunk acknowledgment loss stops publication");
 ck(md::Repository::load(*store,id,draft).payload=="winner","partial replacement leaves prior published bytes intact");
 auto digestDraft=newUuid();bad=parseCanonical(p.manifestBytes());bad.object()["draft_id"]=digestDraft;bad.object()["payload_sha256"]=std::string(64,'c');auto corrupt=canonical(bad);
 ck(store->compareExchangePreferences(newUuid(),md::draftPrefix+digestDraft,1,0,corrupt,true).get().status==Status::Confirmed,"seed contradictory manifest for read refusal");
 r=md::Repository::load(*store,id,digestDraft);ck(r.receipt.status==Status::Unsupported&&r.payload.empty(),"all chunks present but whole payload hash mismatch refuses");
 // A future namespace may already exist in an original profile. A current
 // reader must preserve it and refuse both interpretation and replacement.
 auto futureDraft=newUuid();auto futureKey=md::draftPrefix+futureDraft;auto futureBytes=canonical(Value::Object{{"format","future-manual-draft-v2"}});store.reset();auto futureOptions=o;futureOptions.preferenceValidator=[&](const std::string& k,std::int64_t v,const Value& value){return (k==futureKey&&v==2)||desktop::presentation::composedPreferenceValidator(k,v,value);};store=std::make_unique<ProfileStore>(futureOptions);
 ck(store->compareExchangePreferences(newUuid(),futureKey,2,0,futureBytes,true).get().status==Status::Confirmed,"seed future original namespace with explicit fixture-only validator");store.reset();store=std::make_unique<ProfileStore>(o);
 ck(md::Repository::load(*store,id,futureDraft).receipt.status==Status::Unsupported,"future original draft stays unavailable");auto currentReplacement=md::Repository::prepare(id,futureDraft,"source/test",contract,"must not replace future",1,1);before=writes;
 ck(md::Repository::publish(*store,currentReplacement,true).status==Status::Unsupported&&writes==before,"current save cannot overwrite unsupported future draft");
 ck(store->readPreferences(newUuid(),futureKey).get().data.object().at("bytes").string()==futureBytes,"future original namespace bytes preserved");
 // Actual native manual owner -> profile bytes -> closed/reopened SQLite ->
 // source-bound replay. Storage receipt alone is never native task validation.
 namespace C=tasks::manual_procedure_graph;
 const auto& def=C::definition("exercise-completeness-r01/level054/modulej/p020-u001/practiceprogressioncagedboundariesmasterygateandlog");C::ManualProcedureGraph task(def);
 for(int i=0;i<3;++i){auto input=tests::manual_procedure_fixture::positiveFor(task);const auto action=task.learnerActions().array().front().object().at("action").string();task.apply(task.capture(action),input);}
 auto frozen=task.captureContinuation();const auto taskDraft=newUuid();auto taskSave=md::Repository::prepare(id,taskDraft,def.sourceKey(),def.contractSha256(),frozen.bytes(),frozen.watermark(),0);
 ck(md::Repository::publish(*store,taskSave,true).status==Status::Confirmed,"actual captured manual owner published to isolated profile");store.reset();store=std::make_unique<ProfileStore>(o);auto native=md::Repository::load(*store,id,taskDraft);
 ck(native.receipt.status==Status::Confirmed&&native.payload==frozen.bytes()&&native.watermark==static_cast<std::int64_t>(frozen.watermark()),"normal Store close/reopen retains exact owner continuation");
 auto resumed=C::ManualProcedureGraph::restoreContinuation(def,native.payload);ck(resumed->history()==task.history()&&resumed->learnerView()==task.learnerView()&&resumed->continuation()==frozen.bytes(),"loaded actual owner reconstructs exact next work and original reports");
 auto firstPage=md::Repository::list(*store,id,"",2);ck(firstPage.status==Status::Confirmed&&firstPage.data.object().at("keys").array().size()==2&&firstPage.data.object().at("has_more").boolean(),"bounded key-only draft discovery with more flag");
 auto cursor=firstPage.data.object().at("keys").array().back().string().substr(md::draftPrefix.size());auto nextPage=md::Repository::list(*store,id,cursor,2);ck(nextPage.status==Status::Confirmed&&nextPage.data.object().at("keys").array().front().string()>md::draftPrefix+cursor,"discovery resumes strictly after exact draft cursor");
 ck(store->readPreferenceKeys(newUuid(),md::draftPrefix,"unrelated/cursor",2).get().status==Status::DefiniteFailure,"cross-prefix cursor refused");
 ck(md::Repository::list(*store,newUuid()).status==Status::Conflict,"draft discovery checks actual profile identity");
 auto snapshot=store->snapshot(newUuid()).get();ck(snapshot.status==Status::Confirmed&&snapshot.data.object().at("committed_seq")==Value::fromInteger(0),"private draft saves create no Practice performance or Session fact");
 store.reset();std::cout<<"PASS "<<n<<" manual draft storage checks\n";return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<n<<": "<<e.what()<<'\n';return 1;}}
