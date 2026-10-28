#include "content/Canonical.hpp"
#include <algorithm>
#include <functional>
#include <iostream>
using namespace fathom;
using J=json::Value;
namespace {
int checks=0,failures=0;
void expect(bool pass,const std::string& name){++checks;if(!pass)++failures;std::cout<<(pass?"PASS ":"FAIL ")<<name<<'\n';}
J& f(J& v,const std::string& key){return v.object().at(key);}
const J& f(const J& v,const std::string& key){return v.object().at(key);}
J n(std::int64_t value){return J::fromInteger(value);}
J& rec(J& p,int level){for(auto& r:f(p,"records").array()){std::int64_t l=0;f(r,"legacy_level").integer(l);if(l==level)return r;}throw std::runtime_error("missing control");}
bool has(const content::Result& r,const std::string& code){for(const auto& i:f(r.report,"issues").array())if(f(i,"code").string()==code)return true;return false;}
}
int main(){
 const std::filesystem::path root=FATHOM_SOURCE_ROOT;
 auto read=[&](const char* name){return content::readBounded(root/"Content/controls/representative-v1"/name,32*1024*1024);};
 content::Input input{read("package.json"),read("identity-registry.json"),read("expected-profile.json"),"22c82db322f36d78e744b3445173f7d0a3f4f686ead209293c2416f0db308aed",root};
 const auto package=json::parse(input.package),registry=json::parse(input.registry),profile=json::parse(input.profile);
 const auto base=content::validate(input);expect(base.validReference&&base.exitCode==2&&base.records.size()==13&&base.variants.size()==49,"13candidate controls and49variants valid, never admitted");
 if(!base.validReference)std::cout<<json::stringify(base.report)<<'\n';
 std::size_t events=0,tones=0;for(const auto& r:base.records){events+=r.source.events.size();for(const auto& e:r.source.events)tones+=e.tones.size();expect(!r.source.proposalExample&&!r.readiness.curriculumPlaybackAuthorized,"candidate labelled distinctly, unadmitted "+r.id);}
 expect(events==149&&tones==139,"149source occurrences/139tones");
 for(const auto& v:base.variants){expect(v.source.itemId==v.itemId&&!v.readiness.curriculumPlaybackAuthorized,"variant retains item identity/unadmitted "+v.id);}
 auto variant=[&](const std::string& id)->const content::VariantResult&{auto it=std::find_if(base.variants.begin(),base.variants.end(),[&](const auto& v){return v.id==id;});if(it==base.variants.end())throw std::runtime_error("missing variant");return *it;};
 // Independent requirement-derived representative expectations, not a copy of builder output.
 const auto& l1=variant("fg:variant:000003");expect(l1.source.events.size()==24&&l1.source.events.front().tones[0].string==6&&l1.source.events.back().tones[0].string==1,"L1descending repeats1212 from high to low");
 for(std::size_t i=0;i<l1.source.events.size();++i)expect(l1.source.events[i].tones[0].fret==(i%2==0?5:6)&&!l1.source.events[i].span.onset&&!l1.source.events[i].span.duration,"L1descending source order, no ASCII rhythm "+std::to_string(i));
 expect(!l1.readiness.technicallyRenderable,"unmeteredL1 not ready");
 const auto& l3=variant("fg:variant:000006");expect(l3.source.events.size()==20&&l3.source.events.front().span.duration==Rational(1,4)&&l3.source.events.back().span.onset==Rational(19,4),"L3straight16th exact20-note duration");
 expect(l3.readiness.technicallyRenderable,"even straight16th variant structurally ready");
 expect(!variant("fg:variant:000005").readiness.technicallyRenderable,"after-crossing accent operation not falsely implemented");
 expect(!variant("fg:variant:000014").readiness.technicallyRenderable,"unbound triplet unit not ready");
 const auto& connected=variant("fg:variant:000029");expect(connected.source.events.size()==16&&connected.readiness.technicallyRenderable,"L12connected16-note cell ready");
 expect(!variant("fg:variant:000031").readiness.technicallyRenderable,"L12one-beat pause never silently quarter");
 const auto& triplet=variant("fg:variant:000033");const auto& six=variant("fg:variant:000035");
 expect(triplet.source.events.size()==3&&triplet.source.events[0].span.duration==Rational(1,3),"L15original firsttriplet exactly3notes");
 expect(six.source.events.size()==3&&six.source.events[0].span.duration==Rational(1,6)&&six.source.events[2].span.onset==Rational(1,3),"L15halfmarking structural transform once; no fabricated secondgroup");
 const auto& E=variant("fg:variant:000041");const auto& Em=variant("fg:variant:000042");
 expect(E.source.events.size()==1&&Em.source.events.size()==1&&E.source.events[0].chordSymbol=="E"&&Em.source.events[0].chordSymbol=="Em","E/Em separate alternative projections");
 expect(!E.source.events[0].span.duration&&!Em.source.events[0].span.duration&&!E.readiness.technicallyRenderable,"no invented chord duration");
 for(const auto& r:base.records)if(r.id=="fg:item:000013"||r.id=="fg:item:000012")expect(r.source.events.empty(),"source capstones remain exact task instructions, no inventedscore");
 expect(json::stringify(base.report)==json::stringify(content::validate(input).report),"deterministic candidate report");
 auto mutate=[&](const std::string& name,const std::function<void(J&,J&,J&)>& change,const std::string& code,bool synthetic=true){auto p=package,g=registry,pr=profile;change(p,g,pr);if(synthetic){f(pr,"classification")="synthetic_fixture";f(pr,"reference_package")=p;f(pr,"reference_registry")=g;}const auto bytes=json::stringify(pr);auto result=content::validate({json::stringify(p),json::stringify(g),bytes,content::sha256(bytes),root});expect(!result.validReference&&has(result,code),name+" -> "+code);if(result.validReference||!has(result,code))std::cout<<json::stringify(result.report)<<'\n';};
 auto first=[](J& p,int level)->J&{return f(rec(p,level),"variants").array()[0];};
 mutate("schema/status pairing",[](auto& p,auto&,auto&){f(rec(p,1),"status")="proposal_example";},"SCHEMA_STATUS");
 mutate("schema/classification pairing",[](auto&,auto&,auto& pr){f(pr,"classification")="accepted_contract_reference";},"SCHEMA_CLASSIFICATION",false);
 mutate("candidate fields required",[](auto& p,auto&,auto&){rec(p,1).object().erase("control_scope");},"CANDIDATE_FIELDS");
 mutate("scope count exact",[](auto& p,auto&,auto&){f(f(rec(p,1),"control_scope"),"source_event_count")=n(47);},"CONTROL_EVENT_COVERAGE");
 mutate("unresolved strings typed",[](auto& p,auto&,auto&){f(f(rec(p,1),"control_scope"),"unresolved")=J::Array{false};},"TYPE_STRING");
 mutate("predecessor exact",[](auto& p,auto&,auto&){f(f(rec(p,1),"control_scope"),"proposal_record_sha256")=std::string(64,'0');},"PREDECESSOR_IDENTITY");
 mutate("predecessor authority required",[](auto&,auto&,auto& pr){auto& a=f(pr,"authority_artifacts").array();a.erase(std::remove_if(a.begin(),a.end(),[](const auto& x){return f(x,"role").string()=="predecessor_validation";}),a.end());},"CANDIDATE_AUTHORITY");
 mutate("source basis nonempty",[](auto& p,auto&,auto&){f(f(rec(p,1),"control_scope"),"basis_refs")=J::Array{};},"SOURCE_BASIS_EMPTY");
 mutate("whole workbook not claimed",[](auto& p,auto&,auto&){f(f(rec(p,1),"control_scope"),"whole_workbook_complete")=true;},"WORKBOOK_NOT_COMPLETE");
 mutate("duplicate variant",[](auto& p,auto&,auto&){auto& v=f(rec(p,1),"variants").array();v.push_back(v[0]);},"VARIANT_DUPLICATE");
 mutate("wrong variant parent",[&](auto& p,auto& g,auto&){const auto id=f(first(p,1),"id");for(auto& x:f(g,"entities").array())if(f(x,"id")==id)f(x,"parent")="fg:item:000002";},"VARIANT_PARENT");
 mutate("cross-item event",[&](auto& p,auto&,auto&){f(first(p,1),"event_ids").array()[0]="fg:item:000002:event:0001";},"VARIANT_MEMBERSHIP");
 mutate("duplicate membership",[&](auto& p,auto&,auto&){auto& ids=f(first(p,1),"event_ids").array();ids.push_back(ids[0]);},"DUPLICATE_REFERENCE");
 mutate("source occurrence order",[&](auto& p,auto&,auto&){auto& ids=f(first(p,1),"event_ids").array();std::swap(ids[0],ids[1]);},"VARIANT_ORDER");
 mutate("allocated variant cannot disappear",[](auto& p,auto&,auto&){f(rec(p,1),"variants").array().pop_back();},"VARIANT_ALLOCATION_COVERAGE");
 mutate("event coverage exact",[](auto& p,auto&,auto&){for(auto& v:f(rec(p,1),"variants").array()){auto& ids=f(v,"event_ids").array();if(ids.front().string()=="fg:item:000001:event:0001")ids.erase(ids.begin());}},"VARIANT_EVENT_COVERAGE");
 mutate("source reference bound",[&](auto& p,auto&,auto&){f(first(p,1),"source_refs")=J::Array{"L105-PDF28"};},"SOURCE_REFERENCE_UNDECLARED");
 mutate("pick origin must agree",[&](auto& p,auto&,auto&){f(first(p,1),"pick_start_origin")="not_applicable";},"PICK_ORIGIN");
 mutate("grouping count required",[&](auto& p,auto&,auto&){f(f(first(p,3),"grouping"),"notes_per_beat")=nullptr;},"GROUPING_COUNT");
 mutate("no zero marking",[&](auto& p,auto&,auto&){f(f(first(p,15),"grouping"),"marking_factor")=J::Array{n(0),n(1)};},"POSITIVE_RATIONAL");
 mutate("unused grouping still typed",[&](auto& p,auto&,auto&){f(f(first(p,1),"grouping"),"notes_per_beat")=n(4);},"GROUPING_UNUSED_BINDING");
 mutate("grouping cannot flatten articulation",[](auto& p,auto&,auto&){f(f(rec(p,3),"events").array()[0],"attack")="hammer_on";},"GROUPING_SPAN_SEMANTICS");
 mutate("pause source declared",[](auto& p,auto&,auto&){auto& v=f(rec(p,12),"variants").array()[2];f(f(v,"tail_pause"),"source_ref")="L105-PDF28";},"PAUSE_SOURCE");
 mutate("false runtime admission",[](auto& p,auto&,auto&){f(rec(p,1),"runtime_eligible")=true;},"RUNTIME_NOT_ADMITTED");
 mutate("accepted source rubric cannot be replaced",[](auto& p,auto&,auto&){f(f(rec(p,105),"rubric"),"minimum_total")=n(1);},"RECORD_FIDELITY",false);
 mutate("each selected event source belongs to variant basis",[&](auto& p,auto&,auto&){f(first(p,3),"source_refs")=J::Array{"L3-TXT5-21"};},"VARIANT_EVENT_SOURCE");
 mutate("cumulative grouping overflow has local diagnostic",[&](auto& p,auto&,auto&){auto& g=f(first(p,3),"grouping");f(g,"beat_unit_q")=J::Array{n(9223372036854775807LL),n(1)};f(g,"notes_per_beat")=n(1);},"GROUPING_ARITHMETIC");
 {
  auto p=package,pr=profile;auto& event=f(rec(p,3),"events").array()[20];f(event,"degree_contexts")=J::Object{{"missing-root",J::Object{{"source_label","1"},{"ordinal",n(1)},{"alteration",n(0)}}}};
  f(pr,"classification")="synthetic_fixture";f(pr,"reference_package")=p;const auto bytes=json::stringify(pr);
  const auto r=content::validate({json::stringify(p),input.registry,bytes,content::sha256(bytes),root});
  auto asc=std::find_if(r.variants.begin(),r.variants.end(),[](const auto& v){return v.id=="fg:variant:000006";});
  auto desc=std::find_if(r.variants.begin(),r.variants.end(),[](const auto& v){return v.id=="fg:variant:000010";});
  expect(r.validReference&&has(r,"DEGREE_ROOT_UNBOUND")&&asc!=r.variants.end()&&desc!=r.variants.end()&&asc->readiness.technicallyRenderable&&!desc->readiness.technicallyRenderable,"unbound descending-only degree does not disable ascending variant");
 }
 std::cout<<"CHECKS "<<checks<<" FAILURES "<<failures<<'\n';return failures?1:0;
}
