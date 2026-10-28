#pragma once
#include <juce_gui_basics/juce_gui_basics.h>
#include "storage/Recovery.hpp"
#include "platform/ProfileAccessMac.hpp"
#include "desktop/ReadOnlyTextEditor.hpp"
#include <set>
#include <algorithm>
#include <vector>

namespace fathom::desktop {
// Discovery and selection are read-only. Only an explicit Save creates a
// recovery operation; an uncertain operation remains bound until reconciled.
class OriginalActivityRecovery final : public juce::Component {
public:
    struct Original { storage::RecoveryBinding binding; std::string issue; };
    OriginalActivityRecovery(){
        setComponentID("original-recovery");
        heading_.setText("Recover original activity",juce::dontSendNotification);
        heading_.setFont(juce::FontOptions{24.0f,juce::Font::bold});
        heading_.setColour(juce::Label::textColourId,juce::Colour(0xfff0f4f6));
        originals_.setComponentID("recovery-originals");
        originals_.setTextWhenNothingSelected("Choose the exact original to inspect");
        originals_.setTitle("Choose one retained original. Selection reads its facts and does not save or start activity.");
        originals_.onChange=[this]{
            const auto index=originals_.getSelectedId()-1;
            if(index>=0&&index<int(available_.size())&&selectOriginal(available_[std::size_t(index)].binding.owner))return;
            int original=0;if(binding_)for(std::size_t i=0;i<available_.size();++i)if(available_[i].binding.owner==binding_->owner)original=int(i)+1;
            originals_.setSelectedId(original,juce::dontSendNotification);
        };
        text_.setMultiLine(true);text_.setReadOnly(true);text_.setScrollbarsShown(true);
        text_.setFont(juce::FontOptions{17.0f});text_.setComponentID("recovery-details");
        text_.setTitle("Read-only original recovery facts and next actions. No sound or new activity.");
        text_.setColour(juce::TextEditor::backgroundColourId,juce::Colour(0xff142b38));
        text_.setColour(juce::TextEditor::textColourId,juce::Colour(0xfff0f4f6));
        save_.setComponentID("recovery-save");check_.setComponentID("recovery-check");
        keep_.setComponentID("recovery-keep");details_.setComponentID("recovery-show-details");copy_.setComponentID("recovery-copy-details");
        save_.onClick=[this]{saveOriginal();};check_.onClick=[this]{checkOriginal();};
        keep_.onClick=[this]{detailsShown_=true;kept_=true;refresh();};
        details_.onClick=[this]{detailsShown_=!detailsShown_;refresh();};
        copy_.onClick=[this]{juce::SystemClipboard::copyTextToClipboard(juce::String::fromUTF8(recoveryDetails().c_str()));};
        for(auto* c:std::initializer_list<juce::Component*>{&heading_,&originals_,&text_,&save_,&check_,&keep_,&details_,&copy_})addAndMakeVisible(c);
        int order=2;for(auto* c:std::initializer_list<juce::Component*>{&originals_,&save_,&check_,&keep_,&details_,&copy_,&text_}){c->setWantsKeyboardFocus(true);c->setExplicitFocusOrder(order++);}
        back_.setComponentID("recovery-back");back_.setTitle("Back to the previous page. Keep the original activity and profile unchanged.");back_.setWantsKeyboardFocus(true);back_.setExplicitFocusOrder(1);back_.onClick=[this]{if(suspendPresentation()&&onBack)onBack();};addAndMakeVisible(back_);
        setVisible(false);
    }
    bool attach(storage::ProfileStore& store){
        if(busy()||operation_||!recoveryPrefix_.empty())return false;
        store_=&store;held_=true;suspended_=false;binding_.reset();plan_.reset();available_.clear();
        detailsShown_=false;kept_=false;notice_="Checking retained originals. New activity stays blocked until this read confirms it is safe.";
        readSnapshot();refresh();return true;
    }
    void setProfileIdentity(const std::string& id,const std::string& name,const std::filesystem::path& file){profileSummary_="Profile: "+name+"\nProfile ID: "+id+"\nRecovery file: "+file.string();refresh();}
    std::function<void()> onBack;
    // Back changes presentation only. The held original and any submitted save
    // remain owned here, so hiding this panel cannot admit replacement activity.
    bool suspendPresentation(){if(!held_||busy())return false;suspended_=true;refresh();return true;}
    bool resumePresentation(){if(!held_||busy())return false;suspended_=false;refresh();return true;}
    bool suspended()const noexcept{return suspended_;}
    bool held()const noexcept{return held_;}
    bool busy()const noexcept{return future_.has_value()||(operation_&&!operation_->finished());}
    const std::vector<Original>& originals()const noexcept{return available_;}
    const std::optional<storage::RecoveryBinding>& selectedOriginal()const noexcept{return binding_;}
    bool selectOriginal(const std::string& owner){
        if(!held_||suspended_||busy()||operation_||!recoveryPrefix_.empty())return false;
        const auto it=std::find_if(available_.begin(),available_.end(),[&](const auto& v){return v.binding.owner==owner;});
        if(it==available_.end())return false;
        binding_=it->binding;plan_.reset();kept_=false;state_.clear();
        originals_.setSelectedId(int(it-available_.begin())+1,juce::dontSendNotification);
        if(!it->issue.empty()){notice_="This original's metadata cannot be validated. It is retained; saving is unavailable. Open recovery details for the exact owner and reason.\n"+it->issue;refresh();return true;}
        readingSnapshot_=false;future_.emplace(store_->recoveryState(storage::newUuid(),owner));
        notice_="Reading the selected original. No write or new activity.";refresh();return true;
    }
    const std::string& recoveryOperationId()const noexcept{return recoveryPrefix_;}
    bool saveOriginal(){
        if(!held_||suspended_||busy()||operation_||!recoveryPrefix_.empty()||!binding_||!plan_||plan_->kind==storage::RecoveryKind::NeedsInitialCheckpoint)return false;
        recoveryPrefix_=storage::newUuid();
        if(!startOriginalOperation())return false;
        operationResultShown_=false;kept_=false;notice_="Saving only the selected original while stopped. Keep its profile open until the result is known.";refresh();return true;
    }
    bool checkOriginal(){
        if(!held_||suspended_||busy())return false;
        kept_=false;
        if(operation_){
            if(!operation_->canRetry())return false;
            if(!operation_->retry()){refresh();return false;}
            operationResultShown_=false;notice_="Checking the same original save and operation. No replacement owner, outcome or retry identity.";
        }else if(!recoveryPrefix_.empty()){
            if(!startOriginalOperation())return false;
            operationResultShown_=false;notice_="Checking the retained original submission; no replacement operation.";
        }else if(binding_){
            const auto it=std::find_if(available_.begin(),available_.end(),[&](const auto& v){return v.binding.owner==binding_->owner;});
            if(it==available_.end()||!it->issue.empty())return false;
            readingSnapshot_=false;future_.emplace(store_->recoveryState(storage::newUuid(),binding_->owner));notice_="Checking the selected original's stored facts; no write.";
        }else{readSnapshot();notice_="Checking the retained-original list; no write.";}
        refresh();return true;
    }
    std::string recoveryDetails()const{
        std::string result=profileSummary_+"\n\n"+notice_+"\n\nNew activity and sound remain blocked. Opening these details does not save, delete or replace any original.";
        if(binding_){
            result+="\nOriginal kind: "+binding_->kind+"\nOriginal owner: "+binding_->owner;
            if(binding_->context.isObject())result+="\nOriginal context: "+storage::canonical(binding_->context);
        }else result+="\nChoose one exact original above before saving. No original is selected automatically.";
        if(!recoveryPrefix_.empty())result+="\nRetained recovery operation: "+recoveryPrefix_;
        if(operation_){result+="\nRetained recovery operation: "+operation_->operationPrefix();if(operation_->plan())result+="\nOriginal outcome digest: "+operation_->plan()->digest;result+="\nRecovery code: "+operation_->reply().code;}
        result+="\n\nIf no complete checkpoint or supported action exists, keep this original. Copy these details for support and close normally to retain local data; do not delete or replace the profile. A missing checkpoint cannot be turned into invented practice time or an outcome.";
        return result;
    }
    void poll(){
        if(operation_){
            if(!operation_->finished())operation_->poll();
            if(!operation_->finished()||operationResultShown_)return;
            operationResultShown_=true;const auto& reply=operation_->reply();
            if(reply.status!=storage::Status::Confirmed){
                notice_=(reply.status==storage::Status::Conflict?"Original save conflicts with retained authority. Keep both; no overwrite or replacement retry is available.":"Original save is not confirmed. Keep this original and check the same save when available.")+std::string("\n")+reply.code+": "+reply.message;
                refresh();return;
            }
            operation_.reset();recoveryPrefix_.clear();binding_.reset();plan_.reset();notice_="Original save confirmed. Checking remaining originals; none will be selected automatically.";readSnapshot();refresh();return;
        }
        if(!future_||future_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready)return;
        try{
            auto reply=future_->get();future_.reset();
            if(reply.status!=storage::Status::Confirmed)throw std::runtime_error(reply.code+": "+reply.message);
            if(readingSnapshot_){
                const auto& authority=reply.data.object().at("authoritative").object();std::set<std::string> finals;
                for(const auto& row:authority.at("finalized").array())finals.insert(row.array().at(0).string());
                available_.clear();binding_.reset();plan_.reset();originals_.clear(juce::dontSendNotification);
                for(const auto& row:authority.at("identity").array()){
                    const auto& cells=row.array();if(finals.count(cells.at(0).string()))continue;
                    Original v;v.binding.owner=cells.at(0).string();v.binding.kind=cells.at(1).string();
                    try{storage::validateUuid(v.binding.owner);v.binding.context=storage::parseCanonical(decode(cells.at(4).object().at("blob_hex").string()));storage::validateContext(v.binding.context,v.binding.kind);}
                    catch(const std::exception& e){v.issue=e.what();}
                    available_.push_back(std::move(v));
                }
                std::sort(available_.begin(),available_.end(),[](const auto& a,const auto& b){return a.binding.owner<b.binding.owner;});
                for(std::size_t i=0;i<available_.size();++i)originals_.addItem(juce::String::fromUTF8((available_[i].binding.kind+" — "+available_[i].binding.owner).c_str()),int(i)+1);
                if(available_.empty()){held_=false;notice_.clear();refresh();return;}
                notice_=std::to_string(available_.size())+" original activity record(s) retained. Choose the exact original above to inspect its saved or unsaved facts. No selection saves or starts activity.";
            }else{
                plan_=storage::planRecovery(reply,*binding_);state_=reply.data.object().at("state").string();
                notice_="Selected original: "+binding_->kind+"\nOwner: "+binding_->owner;
                if(plan_->kind==storage::RecoveryKind::NeedsInitialCheckpoint)notice_+="\nNo complete original checkpoint. Saving is unavailable: the app cannot invent an outcome. Keep this original, check its stored state, or open/copy recovery details for support.";
                else{
                    const auto e=storage::validateEnvelope(plan_->bytes);
                    notice_+=state_=="final"?"\nStored outcome found. Confirm the exact original; no new result will be created.":state_=="pending"?"\nOriginal outcome is pending. Save completes only this retained outcome.":"\nComplete checkpoint found. Save recovers only its confirmed facts.";
                    notice_+="\nCaptured: "+e.practiceUtc+" ("+e.timezone+"; local day "+e.day+")\nConfirmed activity: "+std::to_string(e.active.numerator())+"/"+std::to_string(e.active.denominator())+" seconds. Stopped; no sound or new activity.";
                    if(const auto* item=binding_->context.find("item_id");item&&item->isString())notice_+="\nOriginal exercise: "+item->string();
                    if(const auto* variant=binding_->context.find("variant_id");variant&&variant->isString())notice_+=" / "+variant->string();
                }
            }
        }catch(const std::exception& e){future_.reset();plan_.reset();notice_="Originals retained. The read could not establish a safe result: "+std::string(e.what())+"\nCheck again or copy recovery details for support. No write was made by this read.";}
        refresh();
    }
    void paint(juce::Graphics& g)override{g.fillAll(juce::Colour(0xff20252c));}
    void resized()override{
        auto a=getLocalBounds().reduced(24);auto heading=a.removeFromTop(36);back_.setBounds(heading.removeFromRight(100));heading.removeFromRight(12);heading_.setBounds(heading);a.removeFromTop(8);originals_.setBounds(a.removeFromTop(40));a.removeFromTop(12);
        auto lower=a.removeFromBottom(92);auto row=lower.removeFromTop(40);const int w=row.getWidth()/3;save_.setBounds(row.removeFromLeft(w).reduced(4,0));check_.setBounds(row.removeFromLeft(w).reduced(4,0));keep_.setBounds(row.reduced(4,0));lower.removeFromTop(12);details_.setBounds(lower.removeFromLeft(230));lower.removeFromLeft(8);copy_.setBounds(lower.removeFromLeft(230));a.removeFromBottom(10);text_.setBounds(a);
    }
private:
    static std::string decode(const std::string& h){
        if(h.size()%2)throw std::runtime_error("Invalid original context bytes");std::string bytes;
        auto digit=[](char c)->unsigned{if(c>='0'&&c<='9')return unsigned(c-'0');if(c>='a'&&c<='f')return unsigned(c-'a'+10);throw std::runtime_error("Noncanonical original bytes");};
        for(std::size_t i=0;i<h.size();i+=2)bytes.push_back(char((digit(h[i])<<4)|digit(h[i+1])));return bytes;
    }
    bool startOriginalOperation(){
        try{auto original=*binding_;original.originalSealedBytes=plan_->bytes;operation_=std::make_unique<storage::RecoveryOperation>(*store_,std::move(original),recoveryPrefix_);return true;}
        catch(const std::exception& e){notice_="Original submission is not confirmed. Keep its identity and use Check original save; no replacement write.\n"+std::string(e.what());refresh();return false;}
    }
    void readSnapshot(){readingSnapshot_=true;future_.emplace(store_->snapshot(storage::newUuid()));}
    void refresh(){
        setVisible(held_&&!suspended_);if(isVisible())toFront(false);back_.setEnabled(held_&&!busy());
        std::string display=detailsShown_?recoveryDetails():profileSummary_.empty()?notice_:profileSummary_+"\n\n"+notice_;if(kept_)display="Original kept. New activity remains blocked. Inspect or copy the details below, check the same original, or close normally.\n\n"+display;
        text_.setText(juce::String::fromUTF8(display.c_str()),false);
        originals_.setEnabled(held_&&!busy()&&!operation_&&recoveryPrefix_.empty()&&!available_.empty());
        save_.setEnabled(held_&&!busy()&&!operation_&&recoveryPrefix_.empty()&&plan_&&plan_->kind!=storage::RecoveryKind::NeedsInitialCheckpoint);
        check_.setButtonText(!recoveryPrefix_.empty()?"Check original save":"Check stored facts");check_.setEnabled(held_&&!busy()&&(!operation_||operation_->canRetry()));
        keep_.setEnabled(held_&&!busy());details_.setButtonText(detailsShown_?"Back to recovery summary":"Open recovery details");copy_.setEnabled(held_&&binding_.has_value());
    }
    std::string profileSummary_;
    juce::TextButton back_{"Back"};bool suspended_{};
    storage::ProfileStore* store_{};bool held_{},readingSnapshot_{},operationResultShown_{},detailsShown_{},kept_{};
    std::vector<Original> available_;std::optional<storage::ProfileStore::Future> future_;
    std::optional<storage::RecoveryBinding> binding_;std::optional<storage::RecoveryPlan> plan_;
    std::unique_ptr<storage::RecoveryOperation> operation_;std::string notice_,state_,recoveryPrefix_;
    juce::Label heading_;juce::ComboBox originals_;ReadOnlyTextEditor text_;
    juce::TextButton save_{"Save original stopped activity"},check_{"Check stored facts"},keep_{"Keep original and show details"},details_{"Open recovery details"},copy_{"Copy recovery details"};
};
}
