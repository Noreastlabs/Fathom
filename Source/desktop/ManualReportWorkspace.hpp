#pragma once
#include "content/StrictJson.hpp"
#include <vector>

namespace fathom::desktop::manual_workspace {
// Read-only presentation of reports that the native owner already committed.
// Never previews a future form, supplies a report, replays a token, or batches
// native transitions. Original events are copied intact, including retry facts.
inline json::Value reportGroups(const std::vector<json::Value>& history,
                               const json::Value& binding,bool restrictedRole) {
    using V=json::Value;using O=V::Object;using A=V::Array;
    A groups;if(restrictedRole||!binding.isObject())return groups;
    for(const auto* k:{"source_key","contract_sha256","own_closure_sha256"}){
        const auto* v=binding.find(k);if(!v||!v->isString()||v->string().empty())return groups;
    }
    auto falseFlag=[](const V& v,const char*key,bool required=false){const auto*p=v.find(key);return p?(p->isBool()&&!p->boolean()):!required;};
    auto active=[&](const V&v){if(!v.isObject())return false;const auto*p=v.find("state");if(!p||*p!=V("active")||!falseFlag(v,"needs_manual_release",true))return false;for(const auto*k:{"manual_release_debt","external_source_stop_debt","self_check_visible"})if(!falseFlag(v,k))return false;for(const auto*k:{"printed_self_check","printed_reference"})if(const auto*x=v.find(k);x&&!x->null())return false;return true;};
    bool adjacent=false;std::int64_t lastRevision{},lastPass{},lastFrame{};
    for(std::size_t index=0;index<history.size();++index){const auto&e=history[index];bool eligible=e.isObject();std::int64_t revision{},pass{},frame{};
        if(eligible){const auto*a=e.find("action"),*report=e.find("reported"),*before=e.find("before"),*after=e.find("after"),*r=e.find("revision"),*p=e.find("pass");eligible=a&&(*a==V("submit")||*a==V("report"))&&report&&report->isObject()&&!report->object().empty()&&before&&after&&active(*before)&&active(*after)&&r&&r->integer(revision)&&revision>0&&p&&p->integer(pass)&&pass>0&&falseFlag(e,"observed_performance",true)&&falseFlag(e,"grants_credit",true);
            if(const auto*role=e.find("role"))eligible=eligible&&*role==V("learner");
            if(const auto*f=e.find("frame"))eligible=eligible&&f->integer(frame)&&frame>0;
            for(const auto*k:{"source_key","contract_sha256","own_closure_sha256"})if(const auto*x=e.find(k))eligible=eligible&&*x==binding.object().at(k);
        }
        if(!eligible){adjacent=false;continue;}
        if(!adjacent||pass!=lastPass||frame!=lastFrame||revision-lastRevision!=1)groups.emplace_back(O{{"source_binding",binding},{"pass",V::fromInteger(pass)},{"frame",V::fromInteger(frame)},{"reports",A{}}});
        groups.back().object().at("reports").array().emplace_back(O{{"original_event_number",V::fromInteger(static_cast<std::int64_t>(index+1))},{"event",e}});
        adjacent=true;lastRevision=revision;lastPass=pass;lastFrame=frame;
    }
    return groups;
}
}
