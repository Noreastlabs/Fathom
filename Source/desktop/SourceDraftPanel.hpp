#pragma once
#include "desktop/ManualWorkspaceDraft.hpp"
#include "desktop/ReadOnlyTextEditor.hpp"
#include <future>
#include <chrono>

namespace fathom::desktop {
// Host retains the profile Store/lease until every original job is consumed.
// Widget access is confined to Hooks on the message thread. Replay and SQLite
// run in one retained finite worker. Unknown publication is never auto-retried.
class SourceDraftPanel final : public juce::Component {
public:
    using Loaded=storage::manual_drafts::Loaded;
    struct Capture {std::string key,contract,stamp;std::int64_t watermark{};std::function<std::string()> bytes;};
    struct Hooks {
        std::function<Capture()> capture;
        std::function<std::string()> stamp;
        std::function<std::string()> key;
        std::function<void(bool)> freeze;
        std::function<bool()> gate,prepareNavigation,reopenStore;
        std::function<std::function<std::shared_ptr<void>(const Loaded&)>()> decoder;
        std::function<bool(std::shared_ptr<void>,const std::string&)> install;
        std::function<void()> loadRefused; // host may re-present the retained current manual task
    } hooks;
    SourceDraftPanel(){
        setComponentID("source-draft-panel");status_.setComponentID("source-draft-status");status_.setColour(juce::Label::textColourId,juce::Colour(0xff182b33));status_.setText("Open a local profile to save private manual drafts.",juce::dontSendNotification);
        int n=0;for(auto*b:{&save_,&list_,&more_,&open_,&check_,&retry_,&fresh_}){b->setComponentID("source-draft-"+juce::String(++n));addAndMakeVisible(b);}addAndMakeVisible(names_);names_.setComponentID("source-draft-names");names_.setTextWhenNothingSelected("Choose a saved draft for this source");addAndMakeVisible(status_);
        save_.onClick=[this]{save();};list_.onClick=[this]{list(false);};more_.onClick=[this]{list(true);};open_.onClick=[this]{reopen();};check_.onClick=[this]{check();};retry_.onClick=[this]{retry();};fresh_.onClick=[this]{save(true);};controls();
    }
    ~SourceDraftPanel()override{if(job_){try{job_->wait();}catch(...){}}} // host normally drains before destruction
    bool canAttach(const std::string&p)const{return !p.empty()&&!busy()&&!fatal_&&(profile_.empty()||profile_==p);}
    bool attach(storage::ProfileStore&s,const std::string&p){if(!canAttach(p))return false;store_=&s;profile_=p;++attachmentEpoch_;message("Local profile attached. Saving checks its original identity before writing.");return true;}
    bool detach(){if(busy()||fatal_)return false;store_=nullptr;controls();return true;}
    bool busy()const noexcept{return job_.has_value();}
    bool pending()const noexcept{return pending_||fatal_;}
    bool saveForClose(bool gate){if(busy()||pending())return false;if(!hooks.key||hooks.key().empty())return true;if(hooks.stamp&&hooks.stamp()==savedStamp_)return true;save(false,"",gate);return false;}
    bool save(bool asNew=false,const std::string&thenOpen={},bool suppliedGate=true){
        if(!store_||busy()||fatal_||!hooks.capture)return false;if(!allowed()||!suppliedGate){message("Resolve the original audio/activity before saving. Current work remains open.");return false;}
        if(pending_){if(!asNew||(pendingStatus_!=storage::Status::Conflict&&pendingStatus_!=storage::Status::Unsupported))return false;retired_.push_back(pending_);pending_.reset();}
        auto*store=store_;const auto profile=profile_;
        try{freeze(true);auto capture=hooks.capture();if(capture.key.empty())throw std::runtime_error("No current source");
            const bool newId=asNew||id_.empty()||root_!=capture.key||contract_!=capture.contract;const auto id=newId?storage::newUuid():id_;const auto revision=newId?0:revision_;
            job_.emplace(std::async(std::launch::async,[store,profile,capture=std::move(capture),id,revision,thenOpen]()mutable{Work w;w.kind="save";w.key=capture.key;w.contract=capture.contract;w.stamp=capture.stamp;w.id=id;w.revision=revision;w.thenOpen=thenOpen;
                try{auto bytes=capture.bytes();w.publication=std::make_shared<storage::manual_drafts::Publication>(storage::manual_drafts::Repository::prepare(profile,id,capture.key,capture.contract,bytes,capture.watermark,revision));w.publishStarted=true;w.reply=storage::manual_drafts::Repository::publish(*store,*w.publication,true);}catch(const std::exception&e){w.reply=failure(w.publishStarted?storage::Status::Unresolved:storage::Status::DefiniteFailure,e.what());}return w;}));message("Saving private work; original reports remain owned.");return true;
        }catch(const std::exception&){freeze(false);message("Draft saving could not start. Keep current work open; no replacement save was made.");return false;}
    }
    bool list(bool next=false){if(!store_||busy()||pending()||!hooks.key||hooks.key().empty())return false;const auto key=hooks.key(),profile=profile_,after=next?cursor_:std::string{};auto*store=store_;if(!next){names_.clear(juce::dontSendNotification);ids_.clear();}freeze(true);
        job_.emplace(std::async(std::launch::async,[store,profile,key,after]{Work w;w.kind="list";w.key=key;try{w.reply=storage::manual_drafts::Repository::list(*store,profile,after,64);if(w.reply.status==storage::Status::Confirmed){const auto&keys=w.reply.data.object().at("keys").array();w.more=keys.size()==64;for(const auto&item:keys){const auto id=item.string().substr(storage::manual_drafts::draftPrefix.size());w.cursor=id;auto r=store->readPreferences(storage::newUuid(),item.string()).get();if(r.status!=storage::Status::Confirmed)continue;try{auto m=storage::parseCanonical(r.data.object().at("bytes").string());if(!r.data.object().at("applicable").boolean()||m.object().at("source_key")==json::Value(key))w.ids.push_back(id);}catch(const std::exception&){w.ids.push_back(id);}}}}catch(const std::exception&e){w.reply=failure(storage::Status::DefiniteFailure,e.what());}return w;}));message("Reading draft names; originals are unchanged.");return true;
    }
    bool reopen(){if(!store_||busy()||pending()||!allowed()||!hooks.prepareNavigation)return false;const auto selected=names_.getSelectedId();if(selected<1||static_cast<std::size_t>(selected)>ids_.size())return false;const auto target=ids_[selected-1];
        if(!hooks.prepareNavigation()){message("Resolve the actual manual/source release before reopening. Current work remains open.");return false;}
        // Preserve the current closed/fenced workspace under a NEW ID first.
        // Never overwrite the selected saved state just to make reopening safe.
        return save(true,target);
    }
    bool check(){if(!store_||busy()||fatal_||!pending_)return false;if(waitingReopen_&&attachmentEpoch_<=reopenEpoch_){message("Waiting for the original profile to finish reopening; no retry.");return false;}if(waitingReopen_){waitingReopen_=false;needsReopen_=false;}if(needsReopen_||code_=="STORE_UNCERTAIN"){reopenEpoch_=attachmentEpoch_;if(!hooks.reopenStore||!hooks.reopenStore()){message("Keep the original save. Reopen the original profile after actual release, then check it.");return false;}waitingReopen_=true;code_.clear();message("Profile reopen requested. Check the original save when the profile is ready; no retry has started.");return true;}
        auto*store=store_;auto publication=pending_;const auto base=pendingWork_;freeze(true);job_.emplace(std::async(std::launch::async,[store,publication,base]()mutable{auto w=base;w.kind="check";w.publication=publication;try{w.reply=storage::manual_drafts::Repository::reconcile(*store,*publication);}catch(const std::exception&e){w.reply=failure(storage::Status::Unresolved,e.what());}return w;}));message("Checking the same original save; no replacement write.");return true;}
    bool retry(){if(!store_||busy()||fatal_||!pending_||pendingStatus_!=storage::Status::DefinitelyAbsent||!allowed())return false;auto*store=store_;auto publication=pending_;auto base=pendingWork_;freeze(true);job_.emplace(std::async(std::launch::async,[store,publication,base]()mutable{auto w=base;w.kind="save";w.publication=publication;try{w.reply=storage::manual_drafts::Repository::publish(*store,*publication,true);}catch(const std::exception&e){w.reply=failure(storage::Status::Unresolved,e.what());}return w;}));message("Retrying only the checked-absent original publication.");return true;}
    void service(){
        if(!job_||job_->wait_for(std::chrono::milliseconds(0))!=std::future_status::ready)return;Work w;try{w=job_->get();}catch(...){job_.reset();fatal_=true;freeze(false);message("Original worker outcome is unknown. Keep work and the profile retained; no retry or detach.");return;}job_.reset();freeze(false);
        if(w.kind=="list"){if(w.reply.status==storage::Status::Confirmed){for(const auto&id:w.ids){ids_.push_back(id);names_.addItem("Private draft "+juce::String(id.substr(0,8)),static_cast<int>(ids_.size()));names_.getProperties().set(juce::Identifier("draft-"+juce::String(static_cast<int>(ids_.size()))),juce::String(id));}cursor_=w.cursor;moreAvailable_=w.more;message("Saved draft names read. Choose one, then Reopen.");}else message("Draft list unavailable; originals preserved.");controls();return;}
        if(w.kind=="load"){if(w.reply.status==storage::Status::Confirmed&&allowed()&&w.prepared&&hooks.stamp&&hooks.stamp()==w.stamp&&hooks.install&&hooks.install(w.prepared,w.stamp)){id_=w.id;root_=w.key;contract_=w.contract;revision_=w.revision;savedStamp_=hooks.stamp();message("Reopened the source-bound private draft. Provider authorization stays off.");}else {if(hooks.loadRefused)hooks.loadRefused();message("Draft not installed. Current work remains open; no saved bytes were changed.");}controls();return;}
        if(w.reply.status==storage::Status::Confirmed){pending_.reset();pendingWork_=Work{};needsReopen_=waitingReopen_=false;id_=w.id;root_=w.key;contract_=w.contract;revision_=w.revision+1;savedStamp_=w.stamp;const bool same=hooks.stamp&&hooks.stamp()==w.stamp;message(same?"Private draft saved.":"Original draft saved. Newer field edits remain unsaved.");if(!w.thenOpen.empty()&&same)load(w.thenOpen,w.stamp);}
        else if(w.publication){pending_=w.publication;pendingWork_=w;pendingStatus_=w.reply.status;code_=w.reply.code;needsReopen_=w.reply.status==storage::Status::Unresolved;waitingReopen_=false;message("Original draft save needs checking. Its identity and bytes remain retained.");}
        else message("Draft capture refused before publication. Current work is unchanged.");controls();
    }
    void paint(juce::Graphics&g)override{g.fillAll(juce::Colour(0xfff3f6f7));}
    std::string currentDraftId()const{return id_;}
    std::string originalOperationId()const{return pending_?pending_->operationId():std::string{};}
    void resized()override{auto r=getLocalBounds();status_.setBounds(r.removeFromBottom(30));auto top=r.removeFromTop(28);save_.setBounds(top.removeFromLeft(135));list_.setBounds(top.removeFromLeft(135));more_.setBounds(top.removeFromLeft(70));names_.setBounds(top);auto row=r.removeFromTop(28);open_.setBounds(row.removeFromLeft(150));check_.setBounds(row.removeFromLeft(160));retry_.setBounds(row.removeFromLeft(170));fresh_.setBounds(row);}
    const std::string& messageText()const{return message_;}
private:
    struct Work {std::string kind,key,contract,stamp,id,thenOpen,cursor;std::int64_t revision{};bool more{},publishStarted{};storage::Reply reply;std::shared_ptr<storage::manual_drafts::Publication>publication;std::shared_ptr<void>prepared;std::vector<std::string>ids;};
    static storage::Reply failure(storage::Status status,const std::string&s){return{status,"","","SOURCE_DRAFT_WORKER",s,nullptr};}
    bool allowed()const{return hooks.gate&&hooks.gate();}
    void freeze(bool b){if(hooks.freeze)hooks.freeze(b);}
    void message(std::string s){message_=std::move(s);status_.setText(juce::String::fromUTF8(message_.c_str()),juce::dontSendNotification);controls();}
    void controls(){const bool free=store_&&!busy()&&!fatal_;save_.setEnabled(free&&!pending_);list_.setEnabled(free&&!pending_);more_.setEnabled(free&&!pending_&&moreAvailable_);open_.setEnabled(free&&!pending_&&!ids_.empty());check_.setEnabled(free&&pending_);retry_.setEnabled(free&&pending_&&pendingStatus_==storage::Status::DefinitelyAbsent);fresh_.setEnabled(free&&(!pending_||pendingStatus_==storage::Status::Conflict||pendingStatus_==storage::Status::Unsupported));names_.setEnabled(free&&!pending_);}
    void load(const std::string&id,const std::string&stamp){if(!store_||busy()||pending()||!hooks.decoder)return;auto decode=hooks.decoder();if(!decode){message("Open the exact source package before reopening.");return;}auto*store=store_;const auto profile=profile_;freeze(true);job_.emplace(std::async(std::launch::async,[store,profile,id,stamp,decode]{Work w;w.kind="load";w.id=id;w.stamp=stamp;try{const auto loaded=storage::manual_drafts::Repository::load(*store,profile,id);w.reply=loaded.receipt;if(w.reply.status==storage::Status::Confirmed){w.prepared=decode(loaded);w.key=loaded.sourceKey;w.contract=loaded.sourceContract;w.revision=loaded.revision;}}catch(const std::exception&e){w.reply=failure(storage::Status::Unsupported,e.what());}return w;}));message("Checking saved source, fields and original obligations before reopening.");}
    storage::ProfileStore*store_{};std::string profile_,id_,root_,contract_,savedStamp_,cursor_,code_,message_;std::int64_t revision_{};bool fatal_{},moreAvailable_{},needsReopen_{},waitingReopen_{};std::uint64_t attachmentEpoch_{},reopenEpoch_{};std::optional<std::future<Work>>job_;std::shared_ptr<storage::manual_drafts::Publication>pending_;Work pendingWork_;storage::Status pendingStatus_{storage::Status::Confirmed};std::vector<std::shared_ptr<storage::manual_drafts::Publication>>retired_;std::vector<std::string>ids_;
    juce::TextButton save_{"Save private draft"},list_{"Find saved drafts"},more_{"More"},open_{"Reopen selected"},check_{"Check original save"},retry_{"Retry checked save"},fresh_{"Save as new draft"};juce::ComboBox names_;juce::Label status_;
};
}
