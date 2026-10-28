#include "ClosedPackage.hpp"
#include "ClosedPackagePins.hpp"
#include "content/Canonical.hpp"
#include <map>
#include <set>
#include <stdexcept>
namespace fathom::tasks::ear234::package {
namespace {
[[noreturn]] void refuse(const std::string& s){throw std::runtime_error("ear234-package:"+s);}
const json::Value& f(const json::Value& j,const std::string& k){auto p=j.find(k);if(!p)refuse("missing exact field:"+k);return *p;}
std::string sha(const std::string& bytes){
    return fathom::content::sha256(bytes);
}
void exact(const std::string& bytes,std::size_t size,const char* digest,const char* role){
    if(bytes.size()!=size||sha(bytes)!=digest)refuse(std::string("exact byte authority:")+role);
}
}
ClosedPackage ClosedPackage::load(const std::string& bytes,const std::string& index){
    exact(bytes,packageBytes,packageSha,"closed package");exact(index,indexBytes,indexSha,"SourceIndex");
    json::Limits limits;limits.bytes=packageBytes;limits.values=50000;
    auto data=json::parse(bytes,limits);
    if(f(data,"schema").string()!="fathom.ear234.closed-native-package.1")refuse("schema");
    if(f(f(data,"source_index_ref"),"sha256").string()!=indexSha)refuse("SourceIndex join");
    auto& rows=f(data,"rows").array();if(rows.size()!=keys().size()||rows.size()!=234)refuse("closed exact key extent");
    std::set<std::string> seen;
    for(auto& row:rows){auto key=f(row,"source_key").string();if(!seen.insert(key).second)refuse("duplicate exact key");
        auto& d=definition(key);auto& b=d.binding();
        for(auto field:{"source_identity","family","kernel_sha256","contract_sha256","retained_contract_sha256","original_payload_ref","original_canonical_sha256","native_index_binding"})
            if(f(row,field)!=f(b,field))refuse(std::string("compiled source binding:")+field);
    }
    for(auto& key:keys())if(!seen.count(key))refuse("missing compiled key");
    return ClosedPackage(std::move(data));
}
ClosedPackage::ClosedPackage(json::Value data):authority_(std::move(data)){for(auto& row:f(authority_,"rows").array())keys_.push_back(f(row,"source_key").string());}
const Definition& ClosedPackage::lookup(const std::string& key,const std::string& identity)const{
    auto& d=definition(key);if(f(d.binding(),"source_identity").string()!=identity)refuse("foreign source identity");
    return d;
}
std::string ClosedPackage::learnerInstruction(const std::string& key,const std::string& identity)const{
    lookup(key,identity);for(auto& row:f(authority_,"rows").array())if(f(row,"source_key").string()==key)return f(row,"learner_safe_instruction").string();
    refuse("missing instruction");
}
}
