#pragma once
#include "storage/ManualDraftStore.hpp"
#include "tasks/ManualProcedureGraph.hpp"
#include "tasks/OrderedContactTaskFormAdapter.hpp"
namespace fathom::desktop::manual_draft {
using V=json::Value;using O=V::Object;using A=V::Array;namespace C=tasks::manual_procedure_graph;namespace D=storage::manual_drafts;
inline std::string slot(const V& record){return json::stringify(A{record.object().at("role"),record.object().at("action"),record.object().at("watermark")});}
inline void validateForms(const V& forms,std::size_t maximumWatermark){
 D::require(forms.isArray()&&forms.array().size()<=100000,"Private form roster bounds");std::set<std::string> slots;
 for(const auto& record:forms.array()){
  D::require(record.isObject()&&record.object().size()==4,"Private form record shape");const auto& r=record.object();const auto role=r.at("role").string(),action=r.at("action").string();const auto mark=D::integer(r.at("watermark"));
  D::require((role=="learner"||role=="source")&&!action.empty()&&action.size()<=256&&mark>=0&&static_cast<std::size_t>(mark)<=maximumWatermark,"Private form binding");
  const auto& form=r.at("form");D::require(form.isObject()&&form.object().size()==3&&form.object().at("format")==V("typed-manual-form-draft-v1")&&D::digest(form.object().at("schema_sha256").string()),"Private form format");
  D::require(slots.insert(slot(record)).second,"Duplicate private form slot");const auto bytes=json::stringify(form);json::Limits limits;limits.bytes=8*1024*1024;limits.depth=64;limits.values=100000;json::parse(bytes,limits);
 }
}
// The caller must prove this range contains only inactive navigation fences.
// Keep original records; copy learner fields to the new input-token watermark.
// Real reports, role changes and source actions are never crossed.
inline V carryInactiveLearnerForms(const V& forms,std::size_t floor,std::size_t current){
 validateForms(forms,current);D::require(floor<=current,"Inactive form fence range");
 if(floor==current)return forms;
 std::map<std::string,const V*> latest;std::set<std::string> existing;
 for(const auto& record:forms.array()){
  existing.insert(slot(record));const auto& r=record.object();const auto mark=static_cast<std::size_t>(D::integer(r.at("watermark")));
  if(r.at("role")!=V("learner")||mark<floor||mark>=current)continue;
  const auto action=r.at("action").string();const auto old=latest.find(action);
  if(old==latest.end()||D::integer(old->second->object().at("watermark"))<static_cast<std::int64_t>(mark))latest[action]=&record;
 }
 A out=forms.array();for(const auto& entry:latest){auto record=*entry.second;record.object().at("watermark")=V::fromInteger(static_cast<std::int64_t>(current));
  if(existing.count(slot(record)))continue;D::require(out.size()<100000,"Private form roster capacity; original retained");out.push_back(std::move(record));
 }
 return out;
}
inline V formsAcrossInactiveTail(const V& forms,const std::string& continuation){
 json::Limits limits;limits.bytes=D::maxBytes;limits.stringBytes=D::maxBytes;limits.depth=96;limits.values=2000000;
 const auto envelope=json::parse(continuation,limits);const auto& body=envelope.object().at("body");
 D::require(envelope.object().at("sha256")==V(content::sha256(json::stringify(body))),"Inactive form continuation digest");
 const auto& journal=body.object().at("journal").array();std::size_t floor=journal.size();
 while(floor){const auto& e=journal[floor-1];if(!e.isObject()||e.object().size()!=1||!e.find("kind")||e.object().at("kind")!=V("inactive_fence"))break;--floor;}
 return carryInactiveLearnerForms(forms,floor,journal.size());
}
inline std::string encode(const C::PrivateContinuation& owner,const V& forms,const std::string& selectedAction){
 validateForms(forms,owner.watermark());D::require(selectedAction.size()<=256,"Selected draft action bounds");
 auto bytes=storage::canonical(O{{"format","manual-workspace-draft-v1"},{"continuation",owner.bytes()},{"forms",formsAcrossInactiveTail(forms,owner.bytes())},{"selected_action",selectedAction}});D::require(bytes.size()<=D::maxBytes,"Private workspace exceeds save capacity; original remains retained");return bytes;
}
struct Restored {std::unique_ptr<C::ManualProcedureGraph> owner;V forms;std::string action;};
inline Restored decode(const C::Definition& definition,const D::Loaded& loaded){
 D::require(loaded.receipt.status==storage::Status::Confirmed&&loaded.sourceKey==definition.sourceKey()&&loaded.sourceContract==definition.contractSha256(),"Saved workspace source binding differs");
 json::Limits limits;limits.bytes=D::maxBytes;limits.stringBytes=D::maxBytes;limits.depth=96;limits.values=2000000;const auto v=json::parse(loaded.payload,limits);const auto& o=v.object();
 D::require(o.size()==4&&o.at("format")==V("manual-workspace-draft-v1")&&storage::canonical(v)==loaded.payload,"Private workspace version/canonical shape");
 Restored r;r.owner=C::ManualProcedureGraph::restoreContinuation(definition,o.at("continuation").string());D::require(r.owner->continuationWatermark()==static_cast<std::size_t>(loaded.watermark),"Saved workspace watermark differs");r.forms=formsAcrossInactiveTail(o.at("forms"),o.at("continuation").string());validateForms(r.forms,r.owner->continuationWatermark());r.action=o.at("selected_action").string();
 if(!r.action.empty()){bool found=false;const auto available=r.owner->learnerActions();for(const auto& action:available.array())if(action.object().at("action")==V(r.action))found=true;D::require(found,"Saved learner action is not currently available");}
 // Historical Source forms remain private; no live Source role is granted.
 return r;
}
inline std::string contactFormKey(const std::string& action,const V& schema){return action+"@"+content::sha256(json::stringify(schema));}
inline std::string encodeContact(const tasks::ordered_contacts::manual::OrderedContactTaskFormAdapter& adapter,const V& forms,std::optional<tasks::ordered_contacts::manual::Action> selected){
    const auto bytes=adapter.continuation();const auto watermark=adapter.continuationWatermark();validateForms(forms,watermark);
    auto payload=storage::canonical(O{{"format","manual-contact-workspace-draft-v1"},{"continuation",bytes},{"forms",formsAcrossInactiveTail(forms,bytes)},{"selected_action",selected?V::fromInteger(static_cast<int>(*selected)):V{}}});D::require(payload.size()<=D::maxBytes,"Private contact workspace exceeds save capacity; original remains retained");return payload;
}
struct RestoredContact {tasks::ordered_contacts::manual::RestoredContactOwner owner;V forms;std::optional<tasks::ordered_contacts::manual::Action> action;};
inline RestoredContact decodeContact(const tasks::manual_contacts::SourceHandle& source,const D::Loaded& loaded){
    namespace M=tasks::ordered_contacts::manual;
    D::require(loaded.receipt.status==storage::Status::Confirmed&&loaded.sourceKey==source.sourceKey(),"Saved contact source differs");json::Limits limits;limits.bytes=D::maxBytes;limits.stringBytes=D::maxBytes;limits.depth=96;limits.values=2000000;const auto value=json::parse(loaded.payload,limits);const auto& o=value.object();D::require(o.size()==4&&o.at("format")==V("manual-contact-workspace-draft-v1")&&storage::canonical(value)==loaded.payload,"Private contact workspace format differs");
    RestoredContact r;r.owner=M::OrderedContactTaskFormAdapter::restoreContinuation(source,o.at("continuation").string());D::require(r.owner.task->continuationSourceSha256()==loaded.sourceContract&&r.owner.adapter->continuationWatermark()==static_cast<std::size_t>(loaded.watermark),"Saved contact contract or watermark differs");r.forms=formsAcrossInactiveTail(o.at("forms"),o.at("continuation").string());validateForms(r.forms,r.owner.adapter->continuationWatermark());
    if(!o.at("selected_action").null()){const auto n=D::integer(o.at("selected_action"));D::require(n>=0&&n<=static_cast<int>(M::Action::SourceRepairReport),"Saved contact action range");r.action=static_cast<M::Action>(n);D::require(r.owner.adapter->openAction()==r.action,"Saved contact open action differs");}
    return r;
}
} // namespace fathom::desktop::manual_draft
