#include "ClosedPackage.hpp"
#include "ClosedPackagePins.hpp"
#include "content/Canonical.hpp"
#include <set>
#include <stdexcept>
namespace fathom::tasks::c43::package {
namespace {
[[noreturn]]void refuse(const std::string&s){throw std::runtime_error("C43-package:"+s);}
const json::Value&f(const json::Value&j,const std::string&k){auto p=j.find(k);if(!p)refuse("missing field:"+k);return*p;}
std::string sha(const std::string&b){return fathom::content::sha256(b);}
void exact(const std::string&b,std::size_t size,const char*hash,const char*role){if(b.size()!=size||sha(b)!=hash)refuse(std::string("byte authority:")+role);}
}
ClosedPackage ClosedPackage::load(const std::string&bytes,const std::string&index){exact(bytes,packageBytes,packageSha,"closed package");exact(index,indexBytes,indexSha,"SourceIndex");json::Limits l;l.bytes=packageBytes;auto p=json::parse(bytes,l);if(f(p,"schema").string()!="fathom.C43.closed-native-package.1")refuse("schema");
 const auto&native=f(p,"native_implementation_ref");std::int64_t nativeBytes{};
 if(!f(native,"bytes").integer(nativeBytes)||nativeBytes<0||static_cast<std::size_t>(nativeBytes)!=nativeImplementationBytes||f(native,"sha256").string()!=nativeImplementationSha||f(p,"native_semantic_version").string()!=nativeSemanticVersion)refuse("compiled native implementation version");
 auto&rows=f(p,"rows").array();if(rows.size()!=43||rows.size()!=keys().size())refuse("exact extent");std::set<std::string>seen;for(auto&r:rows){auto k=f(r,"source_key").string();if(!seen.insert(k).second)refuse("duplicate key");auto&d=definition(k);for(auto field:{"source_identity","group","native_index_binding","Root_group_contract_ref","Root_group_contract_pointer","source_preimage","original_companion_canonical_sha"})if(f(r,field)!=f(d.binding(),field))refuse(std::string("compiled source join:")+field);}for(auto&k:keys())if(!seen.count(k))refuse("missing key");return ClosedPackage(std::move(p));}
ClosedPackage::ClosedPackage(json::Value p):authority_(std::move(p)){}
const Definition&ClosedPackage::lookup(const std::string&key,const std::string&identity)const{auto&d=definition(key);if(f(d.binding(),"source_identity").string()!=identity)refuse("foreign source identity");return d;}
std::string ClosedPackage::learnerInstruction(const std::string&key,const std::string&identity)const{lookup(key,identity);for(auto&r:f(authority_,"rows").array())if(f(r,"source_key").string()==key)return f(r,"learner_safe_instruction").string();refuse("missing instruction");}
}
