#include "tasks/BoundSourceUnits.hpp"
#include "content/Canonical.hpp"
#include <GeneratedB714Bindings.hpp>
#include <chrono>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>

namespace {
std::size_t checks=0;
void require(bool x,const char* why){++checks;if(!x)throw std::runtime_error(why);}
}
int main(){
 try{
  namespace bound=fathom::tasks::bound_source_units;
  namespace b714_compiled_generated=fathom::tasks::b714_compiled_generated;
  const auto start=std::chrono::steady_clock::now();
  const auto& rows=bound::rows(); // Reconstructs and verifies every program.
  const auto initialized=std::chrono::steady_clock::now();
  require(rows.size()==b714_compiled_generated::rowCount,"closed row count");
  std::set<std::string> keys,kinds;
  std::string digestInput;
  for(std::size_t i=0;i<rows.size();++i){
   const auto& actual=rows[i];const auto& expected=b714_compiled_generated::rows[i];
   require(std::string(actual.key)==expected.key,"source order/key");
   require(std::string(actual.value)==expected.value,"complete export bytes");
   require(std::string(actual.original)==expected.original,"complete original bytes");
   require(std::string(actual.closure)==expected.closure,"complete source closure bytes");
   require(keys.insert(actual.key).second&&bound::exactKey(actual.key),"exact unique key");
   require(bound::cagedKey(actual.key)==expected.caged,"caged membership");
   require(bound::triadControlsKey(actual.key)==expected.triad,"triad membership");
   require(bound::coordinateOverrideKey(actual.key)==expected.coordinate,"coordinate membership");
   const auto exported=fathom::json::parse(actual.value);
   const auto* program=exported.find("program");require(program!=nullptr,"complete program");
   const auto* facts=program->find("source_facts");require(facts!=nullptr,"operative facts");
   require(bound::operativeImplementation(actual.key)==*facts,"exact operative implementation");
   const auto* kind=facts->find("kind");require(kind&&kind->isString()&&bound::allowedKind(kind->string()),"exact known kind");
   kinds.insert(kind->string());
   digestInput+=actual.key;digestInput+='\n';digestInput+=actual.value;digestInput+='\n';digestInput+=actual.original;digestInput+='\n';digestInput+=actual.closure;digestInput+='\n';
  }
  std::map<std::string,std::string> expectedContexts;
  for(const auto& x:b714_compiled_generated::generated::contexts)expectedContexts.emplace(x.path,x.value);
  const auto& contexts=bound::contexts();std::set<std::string> contextKeys;
  for(const auto& x:contexts){require(contextKeys.insert(x.path).second,"unique context");require(expectedContexts.at(x.path)==x.value,"complete context bytes");}
  require(!bound::exactKey("foreign/source/key"),"foreign key refused");
  require(!bound::allowedKind("foreign_kind"),"foreign kind refused");
  require(!bound::cagedKey("foreign/source/key")&&!bound::triadControlsKey("foreign/source/key")&&!bound::coordinateOverrideKey("foreign/source/key"),"foreign memberships refused");
  bool refused=false;try{bound::operativeImplementation("foreign/source/key");}catch(const std::runtime_error&){refused=true;}require(refused,"foreign operative lookup refused");
  require(bound::cachedFilesHashed()==0,"no runtime source cache read");
  require(&bound::rows()==&rows&&&bound::contexts()==&contexts,"stable initialized storage");
  const auto done=std::chrono::steady_clock::now();
  std::cout<<"{\"result\":\"PASS\",\"rows\":"<<rows.size()<<",\"contexts\":"<<contexts.size()<<",\"kinds\":"<<kinds.size()<<",\"checks\":"<<checks
   <<",\"initialization_seconds\":"<<std::chrono::duration<double>(initialized-start).count()
   <<",\"total_seconds\":"<<std::chrono::duration<double>(done-start).count()
   <<",\"complete_bound_row_digest\":\""<<fathom::content::sha256(digestInput)<<"\",\"source_files_hashed\":0}"<<std::endl;
  return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL after "<<checks<<" checks: "<<e.what()<<std::endl;return 1;}
}
