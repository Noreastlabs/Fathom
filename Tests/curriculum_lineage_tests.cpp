#include "content/Canonical.hpp"
#include <algorithm>
#include <fstream>
#include <functional>
#include <iostream>
#include <tuple>
using namespace fathom;
using J=json::Value;
namespace {
J& f(J& j,const std::string& k){return j.object().at(k);}
const J& f(const J& j,const std::string& k){return j.object().at(k);}
J& item(J& p,const std::string& id){for(auto& x:f(p,"records").array())if(f(x,"id").string()==id)return x;throw std::runtime_error("missing item");}
bool has(const content::Result& r,const std::string& code){for(const auto& x:f(r.report,"issues").array())if(f(x,"code").string()==code)return true;return false;}
}
int main(int argc,char** argv){
 if(argc!=3)return 64;
 const std::filesystem::path root=FATHOM_SOURCE_ROOT,fixture=argv[1],out=argv[2];
 if(!std::filesystem::create_directory(out))return 73;
 std::size_t checks=0,failures=0;J::Array results;
 auto check=[&](bool pass,const std::string& name){++checks;if(!pass)++failures;results.emplace_back(J::Object{{"name",name},{"pass",pass}});std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';};
 auto read=[&](const std::string& name){return content::readBounded(fixture/name,32*1024*1024);};
 auto fixturePackage=json::parse(read("package.json")),fixtureProfile=json::parse(read("expected-profile.json"));
 const auto profileBytes=json::stringify(fixtureProfile);
 content::Input input{json::stringify(fixturePackage),read("identity-registry.json"),profileBytes,content::sha256(profileBytes),root};
 const auto package=json::parse(input.package),registry=json::parse(input.registry),profile=json::parse(input.profile);
 const auto base=content::validate(input);std::ofstream(out/"base-report.json")<<json::stringify(base.report)<<'\n';
 check(base.validReference&&base.exitCode==2&&base.records.size()==14&&base.variants.size()==53,"14 source examples and53variants validate without admission");
 std::size_t events=0;for(const auto& rr:base.records){events+=rr.source.events.size();check(!rr.source.proposalExample&&!rr.readiness.curriculumPlaybackAuthorized,"converted but unadmitted "+rr.id);}
 check(events==197,"197 retained source occurrences");
 auto old=json::parse(content::readBounded(root/"Content/controls/representative-v1/package.json",32*1024*1024));
 for(const auto& prior:f(old,"records").array()){
  auto current=package;auto transformed=item(current,f(prior,"id").string());
  transformed.object().erase("lineage");f(transformed,"content_revision")=f(prior,"content_revision");f(transformed,"control_scope").object()["proposal_record_sha256"]=f(f(prior,"control_scope"),"proposal_record_sha256");
  check(transformed==prior,"all previous source/rubric fields retained "+f(prior,"id").string());
 }
 for(const auto& rr:base.records)if(rr.id=="fg:item:000014"){
  check(rr.source.events.size()==48&&!rr.readiness.technicallyRenderable,"new source48events remains untimed/unrenderable");
  for(std::size_t i=0;i<rr.source.events.size();++i){const auto& ev=rr.source.events[i];const int fret=5+(i%4==1?1:i%4==3?2:0);const auto string=i<24?i/4+1:6-(i-24)/4;
   check(ev.tones.size()==1&&ev.tones[0].fret==fret&&ev.tones[0].string==static_cast<int>(string)&&!ev.span.onset&&!ev.span.duration,"actual1213 direction occurrence "+std::to_string(i));
  }
 }
 check(json::stringify(base.report)==json::stringify(content::validate(input).report),"repeat validation deterministic");
 auto mutate=[&](const std::string& name,const std::function<void(J&,J&,J&)>& change,const std::string& code){
  auto p=package,g=registry,pr=profile;change(p,g,pr);f(pr,"classification")="synthetic_fixture";f(pr,"reference_package")=p;f(pr,"reference_registry")=g;const auto pb=json::stringify(pr);
  auto result=content::validate({json::stringify(p),json::stringify(g),pb,content::sha256(pb),root});
  check(!result.validReference&&has(result,code),name+" -> "+code);std::ofstream(out/(std::to_string(checks)+"-negative.json"))<<json::stringify(result.report)<<'\n';
 };
 const std::string oldid="fg:item:000001",newid="fg:item:000014";
 mutate("unknownschema",[](auto& p,auto&,auto&){f(p,"schema_version")="unsupported";},"UNSUPPORTED_VALUE");
 mutate("missinglineage",[&](auto& p,auto&,auto&){item(p,newid).object().erase("lineage");},"LINEAGE_REQUIRED");
 mutate("oldasnew",[&](auto& p,auto&,auto&){f(item(p,oldid),"lineage")=J::Object{{"kind","new"}};f(item(p,oldid),"content_revision")=J::fromInteger(1);},"LINEAGE_NEW");
 mutate("newfalsepredecessor",[&](auto& p,auto&,auto&){f(item(p,newid),"lineage")=f(item(p,oldid),"lineage");f(item(p,newid),"content_revision")=J::fromInteger(3);},"LINEAGE_PREDECESSOR");
 mutate("newrevisionnotone",[&](auto& p,auto&,auto&){f(item(p,newid),"content_revision")=J::fromInteger(2);},"LINEAGE_NEW");
 mutate("wrongdigest",[&](auto& p,auto&,auto&){f(f(item(p,oldid),"lineage"),"predecessor_sha256")=std::string(64,'0');},"LINEAGE_PREDECESSOR");
 mutate("wrongpriorrevision",[&](auto& p,auto&,auto&){f(f(item(p,oldid),"lineage"),"predecessor_revision")=J::fromInteger(1);},"LINEAGE_PREDECESSOR");
 mutate("revisionreused",[&](auto& p,auto&,auto&){f(item(p,oldid),"content_revision")=J::fromInteger(2);},"LINEAGE_REVISION");
 mutate("revisionskipped",[&](auto& p,auto&,auto&){f(item(p,oldid),"content_revision")=J::fromInteger(4);},"LINEAGE_REVISION");
 mutate("crossednewfields",[&](auto& p,auto&,auto&){f(item(p,newid),"lineage").object()["predecessor_revision"]=J::fromInteger(2);},"UNKNOWN_FIELD");
 mutate("oldscopefieldin1",[&](auto& p,auto&,auto&){f(item(p,newid),"control_scope").object()["proposal_record_sha256"]=std::string(64,'0');},"UNKNOWN_FIELD");
 mutate("falseadmission",[&](auto& p,auto&,auto&){f(item(p,newid),"runtime_eligible")=true;},"RUNTIME_NOT_ADMITTED");
 mutate("falseworkbook",[&](auto& p,auto&,auto&){f(f(item(p,newid),"control_scope"),"whole_workbook_complete")=true;},"WORKBOOK_NOT_COMPLETE");
 mutate("oldreparent",[&](auto&,auto& g,auto&){for(auto& ent:f(g,"entities").array())if(f(ent,"id").string()==oldid)f(ent,"parent")="fg:module:000014";},"IDENTITY_REASSIGNED");
 for(const auto role:{"identity_baseline","allocation_baseline","lineage_baseline"})mutate(std::string("missing ")+role,[&](auto&,auto&,auto& pr){auto& a=f(pr,"authority_artifacts").array();a.erase(std::remove_if(a.begin(),a.end(),[&](const auto& x){return f(x,"role").string()==role;}),a.end());},"BASELINE_REQUIRED");
 mutate("knownrequiresreport",[](auto&,auto&,auto& pr){auto& a=f(pr,"authority_artifacts").array();a.erase(std::remove_if(a.begin(),a.end(),[](const auto& x){return f(x,"role").string()=="predecessor_validation";}),a.end());},"LINEAGE_PREDECESSOR");
 // A source-only catalog is a schema1 metadata companion, never playback admission.
 const auto currentPackage=json::parse(content::readBounded(root/"Content/controls/curriculum-v1/package.json",32*1024*1024));
 auto catalog=f(currentPackage,"workbook_catalog");
 check(f(catalog,"entries").array().size()==105&&f(catalog,"inventory_bindings").array().size()==105,
       "current catalog retains all105 source-only entries");
 {
  auto p=package,g=registry,pr=profile;p.object()["workbook_catalog"]=catalog;
  g.object()["workbook_catalog"]=catalog;pr.object()["workbook_catalog"]=catalog;
  const auto bytes=json::stringify(pr);
  auto result=content::validate({json::stringify(p),json::stringify(g),bytes,content::sha256(bytes),root});
  check(result.validReference&&result.exitCode==2&&result.records.size()==14,
        "all105 current source-only entries pass schema1 catalog validation without admission");
 }
 auto small=catalog;
 f(small,"entries").array().resize(2);f(small,"inventory_bindings").array().resize(2);
 f(f(small,"scope"),"entry_count")=J::fromInteger(2);f(f(small,"scope"),"last_level")=J::fromInteger(2);
 f(f(small,"scope"),"wbs_owners")=J::Array{"2.3.1.1.1"};
 auto catalogInput=[&](const J& p,const J& g,const J& pr){const auto bytes=json::stringify(pr);return content::Input{json::stringify(p),json::stringify(g),bytes,content::sha256(bytes),root};};
 auto withCatalog=[&](){auto p=package,g=registry,pr=profile;p.object()["workbook_catalog"]=small;g.object()["workbook_catalog"]=small;pr.object()["workbook_catalog"]=small;return std::tuple<J,J,J>{p,g,pr};};
 {
  auto [p,g,pr]=withCatalog();auto result=content::validate(catalogInput(p,g,pr));
  check(result.validReference&&result.exitCode==2&&result.records.size()==14,
        "schema1 source-only catalog companion validates without runtime admission");
  check(std::none_of(result.records.begin(),result.records.end(),[](const auto& rr){return rr.readiness.curriculumPlaybackAuthorized;}),
        "catalog cannot authorize playback");
 }
 auto catalogNegative=[&](const std::string& name,const std::function<void(J&,J&,J&)>& change,const std::string& code){
  auto [p,g,pr]=withCatalog();change(p,g,pr);auto result=content::validate(catalogInput(p,g,pr));
  check(!result.validReference&&has(result,code),name+" -> "+code);
 };
 catalogNegative("catalog registry drift",[](auto&,auto& g,auto&){f(f(f(g,"workbook_catalog"),"inventory_map"),"sha256")=std::string(64,'0');},"CATALOG_FIDELITY");
 catalogNegative("catalog profile missing",[](auto&,auto&,auto& pr){pr.object().erase("workbook_catalog");},"CATALOG_BINDING");
 catalogNegative("catalog duplicate level",[](auto& p,auto&,auto&){f(f(p,"workbook_catalog"),"inventory_bindings").array()[1].object()["level"]=J::fromInteger(1);},"CATALOG_DUPLICATE");
 catalogNegative("catalog duplicate TXT path",[](auto& p,auto&,auto&){auto& entries=f(f(p,"workbook_catalog"),"entries").array();f(f(entries[1],"txt"),"path")=f(f(entries[0],"txt"),"path");},"CATALOG_DUPLICATE");
 catalogNegative("catalog level out of range",[](auto& p,auto&,auto&){f(f(p,"workbook_catalog"),"inventory_bindings").array()[1].object()["level"]=J::fromInteger(106);},"INTEGER_RANGE");
 catalogNegative("catalog unsafe TXT path",[](auto& p,auto&,auto&){f(f(f(p,"workbook_catalog"),"entries").array()[0],"txt").object()["path"]="../outside.txt";},"CATALOG_PATH");
 catalogNegative("catalog false runtime admission",[](auto& p,auto&,auto&){f(f(p,"workbook_catalog"),"entries").array()[0].object()["runtime_eligible"]=true;},"CATALOG_NOT_ADMITTED");
 catalogNegative("catalog rejected in legacy schema",[](auto& p,auto&,auto&){f(p,"schema_version")="0.2.0-control-candidate";},"UNKNOWN_FIELD");
 J summary=J::Object{{"status",failures?"FAIL":"PASS"},{"checks",J::fromInteger(static_cast<std::int64_t>(checks))},{"failures",J::fromInteger(static_cast<std::int64_t>(failures))},{"classification","source-bound fixtures and synthetic counterexamples; no runtime/human admission"},{"results",results}};
 std::ofstream(out/"summary.json")<<json::stringify(summary)<<'\n';return failures?1:0;
}
