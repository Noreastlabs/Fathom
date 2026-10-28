#pragma once
// REVIEWER TEST SUPPORT ONLY. No admitted curriculum, actual work or completion verdict.
#include "storage/StorageEnvelope.hpp"
#include "content/Canonical.hpp"
#include <set>

namespace reviewer::synthetic {
using fathom::storage::Value;
class L105SourceHandler final {
    Value authority_, context_;
    static const Value& at(const Value& v,const std::string& k) {
        auto p=v.find(k); if(!p)throw std::runtime_error("Missing semantic field: "+k);return *p;
    }
    static void need(bool b){if(!b)throw std::runtime_error("Unsupported synthetic L105 assertion");}
    static bool text(const Value& v){return v.isString()&&!v.string().empty()&&v.string().find_first_not_of(" \t\r\n")!=std::string::npos;}
    static bool integer(const Value& v,std::int64_t& n){return v.integer(n)&&n>=0&&fathom::storage::canonical(v)==std::to_string(n);}
    static void scores(const Value& assertion,const Value& rubric) {
        const auto* s=assertion.find("scores");const auto* total=assertion.find("total");
        if(!s||s->null()){need(!total||total->null());return;}
        need(s->isObject());std::set<std::string> names;std::int64_t sum=0;
        for(const auto& d:at(rubric,"dimensions").array()){
            const auto& name=at(d,"name").string();names.insert(name);std::int64_t n=0;
            need(integer(at(*s,name),n)&&n<static_cast<std::int64_t>(at(d,"anchors").array().size()));sum+=n;
        }
        need(s->object().size()==names.size());
        if(total&&!total->null()){std::int64_t n=0;need(integer(*total,n)&&n==sum);}
        // No minimum-total/protected-zero admission rule: valid incomplete work is retained.
    }
    static void booleanMap(const Value* v,const Value& allowed) {
        if(!v)return;need(v->isObject());std::set<std::string> names;
        for(const auto& name:allowed.array())names.insert(name.string());
        for(const auto& p:v->object())need(names.count(p.first)==1&&p.second.isBool());
        // Missing/false obligations, constraints and outputs are incomplete, not malformed.
    }
public:
    L105SourceHandler(const std::string& authorityBytes,Value standaloneContext):authority_(fathom::json::parse(authorityBytes)),context_(std::move(standaloneContext)){
        need(fathom::content::sha256(authorityBytes)=="b2e44dece9777ac1cab3aa6a3402936038f5ae586d2d184d4bb1976c494f4ab6");
        need(fathom::content::sha256(fathom::storage::canonical(context_))=="7cb026b52bdc5b628b0814bbdf29b8114a7ed5416d968d7815611c8367e785e1");
        const auto& record=at(authority_,"canonical_record");const auto& rule=at(authority_,"source_rule");
        need(at(record,"id")==Value("fg:item:000013")&&at(record,"content_revision")==Value::fromInteger(1));
        need(at(record,"runtime_eligible")==Value(false)&&at(record,"rubric")==at(rule,"rubric")&&at(record,"source_refs")==at(rule,"source_refs"));
    }
    bool operator()(const Value& v)const noexcept{
        try{
            const auto& c=at(v,"context");const auto& ref=at(v,"rubric_ref");const auto& a=at(v,"attestation");
            need(c==context_&&at(v,"item_id")==at(c,"item_id")&&at(v,"content_revision")==at(c,"content_revision"));
            for(auto k:{"item_id","content_revision","content_version"})need(at(ref,k)==at(c,k));
            need(at(ref,"source_rules_version")==at(authority_,"source_rules_version")&&at(ref,"rubric_sha256")==at(authority_,"rubric_sha256"));
            const auto& rubric=at(at(authority_,"canonical_record"),"rubric");const auto& resource=at(authority_,"resource_plan_entry");
            need(a.isObject()&&at(a,"actual_work")==Value(true));
            scores(a,rubric);booleanMap(a.find("obligations"),at(rubric,"required_obligations"));
            const auto& resources=at(a,"resources");need(resources.isObject()&&resources.object().size()==1);
            const auto& r=at(resources,"R105");need(r.isObject()&&at(r,"actual_access")==Value(true)&&text(at(r,"work_ref")));
            std::set<std::string> resourceKeys{"actual_access","work_ref","constraints","outputs"};
            for(const auto& p:r.object())need(resourceKeys.count(p.first)==1);
            booleanMap(r.find("constraints"),at(resource,"selection_constraints"));
            booleanMap(r.find("outputs"),at(resource,"required_outputs"));
            if(const auto* q=a.find("independent");q&&!q->null()&&*q!=Value(false)){need(q->isObject());scores(*q,rubric);}
            return true; // Storage admissibility only. NEVER a SourceComplete/reviewer acceptance result.
        }catch(...){return false;}
    }
};
} // namespace reviewer::synthetic
