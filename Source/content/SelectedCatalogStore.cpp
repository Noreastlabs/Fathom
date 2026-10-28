#include "content/SelectedCatalogStore.hpp"
#include "content/InstalledExtensionRegistry.hpp"
#include <algorithm>

namespace fathom::lesson {
namespace {
void require(bool ok,const std::string& message){if(!ok)throw std::invalid_argument(message);}
void explicitPath(const std::filesystem::path& path){
    require(path.is_absolute(),"Selected catalog requires absolute installed paths");
    for(const auto& part:path)require(part!="."&&part!="..","Selected catalog paths must not contain dot traversal");
}
std::map<std::string,std::string> requests(const std::vector<SelectedCatalogStore::Request>& input){
    std::map<std::string,std::string> result;
    for(const auto& request:input){
        require(!request.itemId.empty(),"Selected catalog requires an explicit item identity");
        const auto& hash=request.expectedPackageHash;
        require(hash.empty()||(hash.size()==64&&std::all_of(hash.begin(),hash.end(),[](char c){return (c>='0'&&c<='9')||(c>='a'&&c<='f');})),
            "Selected catalog package identity must be an exact SHA-256");
        const auto inserted=result.emplace(request.itemId,hash);
        if(!inserted.second){
            auto& previous=inserted.first->second;
            require(previous.empty()||hash.empty()||previous==hash,"Conflicting package identities for selected item");
            if(previous.empty())previous=hash;
        }
    }
    return result;
}
}
SelectedCatalogStore::SelectedCatalogStore(std::filesystem::path base,
    std::vector<std::filesystem::path> exactInstalledExtensions)
 :base_(std::move(base)),extensions_(std::move(exactInstalledExtensions)){
    explicitPath(base_);
    require(base_.filename()=="representative-controls","Selected catalog requires the explicit installed base bundle");
    const auto& descriptors=installedExtensionDescriptors();
    require(extensions_.size()==descriptors.size(),"Selected catalog requires the complete exact compiled extension path vector");
    for(std::size_t i=0;i<descriptors.size();++i){
        explicitPath(extensions_[i]);
        require(extensions_[i]==base_.parent_path()/descriptors[i].directory,
            "Selected catalog extension path differs from its exact compiled owner");
        require(itemOwners_.emplace(descriptors[i].item,i).second,"Duplicate compiled installed item owner");
        for(const auto& selected:descriptors[i].additionalCases)
            require(itemOwners_.emplace(selected.item,i).second,"Duplicate compiled installed item owner");
    }
}
std::vector<std::string> SelectedCatalogStore::requiredOwners(const std::vector<Request>& input) const{
    const auto selected=requests(input);
    std::set<std::size_t> owners;
    for(const auto& item:selected){const auto owner=itemOwners_.find(item.first);if(owner!=itemOwners_.end())owners.insert(owner->second);}
    std::vector<std::string> names{"representative-controls"};
    for(const auto owner:owners)names.emplace_back(installedExtensionDescriptors()[owner].directory);
    return names;
}
std::vector<std::string> SelectedCatalogStore::cachedOwnerNames() const{
    std::lock_guard<std::mutex> lock(stateMutex_);
    std::vector<std::string> names;
    for(const auto& entry:cache_)names.push_back(entry.first);
    return names;
}
std::vector<std::string> SelectedCatalogStore::preparedOwnerNames() const{
    std::lock_guard<std::mutex> lock(stateMutex_);return preparedNames_;
}
SelectedCatalogStore::Preparation SelectedCatalogStore::lastPreparation() const{
    std::lock_guard<std::mutex> lock(stateMutex_);return last_;
}
std::uint64_t SelectedCatalogStore::revision() const{
    std::lock_guard<std::mutex> lock(stateMutex_);return revision_;
}
std::shared_ptr<const Catalog> SelectedCatalogStore::prepare(const std::vector<Request>& input,
    std::function<bool()> canceled){
    std::lock_guard<std::mutex> prepareLock(preparationMutex_);
    const auto selected=requests(input);
    const auto names=requiredOwners(input);
    Preparation observation;observation.requiredOwners=names;
    const auto recordCanceled=[&]{
        std::lock_guard<std::mutex> lock(stateMutex_);
        observation.canceled=true;observation.preparedOwners=preparedNames_;observation.revision=revision_;last_=observation;
    };
    const auto stop=[&]{
        if(!canceled||!canceled())return false;
        recordCanceled();
        return true;
    };
    if(stop())return {};
    const auto& descriptors=installedExtensionDescriptors();
    std::map<std::string,std::shared_ptr<const Catalog>> verified;
    try{
        for(const auto& name:names){
            if(stop())return {};
            const InstalledExtensionDescriptor* descriptor=nullptr;
            auto path=base_;
            if(name!="representative-controls"){
                const auto found=std::find_if(descriptors.begin(),descriptors.end(),[&](const auto& d){return name==d.directory;});
                require(found!=descriptors.end(),"Requested installed owner is not compiled");
                descriptor=&*found;path=extensions_[static_cast<std::size_t>(found-descriptors.begin())];
            }
            std::shared_ptr<const Catalog> cached;
            {std::lock_guard<std::mutex> lock(stateMutex_);const auto found=cache_.find(name);if(found!=cache_.end())cached=found->second;}
            try{
                if(cached){
                    const auto identity=Catalog::reverifyBundle(path,descriptor,cached->validation_,canceled);
                    require(identity.manifestHash==cached->manifestHash_&&identity.packageHash==cached->packageHash_&&identity.transportHash==cached->transportHash_,
                        "Cached lesson source identity differs from current complete bundle");
                    ++observation.memoryCacheHits;observation.recheckedAssets+=identity.assetCount;observation.recheckedBytes+=identity.assetBytes;
                }else{
                    cached=descriptor?Catalog::loadExtension(path,*descriptor,canceled):Catalog::load(path,canceled);
                    ++observation.loadedOwners;
                    std::lock_guard<std::mutex> lock(stateMutex_);cache_[name]=cached;
                }
            }catch(const content::LoadCanceled&){
                throw; // Interrupted checking does not invalidate a verified snapshot.
            }catch(...){
                std::lock_guard<std::mutex> lock(stateMutex_);cache_.erase(name);throw;
            }
            verified.emplace(name,std::move(cached));
        }
        if(stop())return {};
        const auto& original=verified.at("representative-controls");
        // Check every requested identity against its compiled owner before any
        // union is published, including base-only identities and exact hashes.
        for(const auto& item:selected){
            if(stop())return {};
            const auto owner=itemOwners_.find(item.first);
            const auto& catalog=owner==itemOwners_.end()?original:verified.at(descriptors[owner->second].directory);
            catalog->lesson(item.first);
            require(item.second.empty()||catalog->packageHash_==item.second,
                "Selected item package hash differs from its exact installed source");
        }
        if(stop())return {};
        // A warm request for the same scope returns the same immutable union;
        // it still performed complete current byte checks above.
        {
            std::lock_guard<std::mutex> lock(stateMutex_);
            if(prepared_&&preparedNames_==names){
                observation.preparedOwners=preparedNames_;observation.revision=revision_;last_=observation;
                return prepared_;
            }
        }
        auto catalog=std::shared_ptr<Catalog>(new Catalog(*original));
        std::set<std::string> items,variants;
        for(const auto& lesson:catalog->lessons_){items.insert(lesson.id);for(const auto& variant:lesson.variants)variants.insert(variant.id);}
        for(std::size_t i=1;i<names.size();++i){
            if(stop())return {};
            const auto& added=verified.at(names[i]);
            if(names[i]=="level001-extension"){
                const auto originalItem=std::find_if(catalog->lessons_.begin(),catalog->lessons_.end(),[](const Lesson& lesson){return lesson.id=="fg:item:000001";});
                require(originalItem!=catalog->lessons_.end()&&std::count_if(catalog->lessons_.begin(),catalog->lessons_.end(),[](const Lesson& lesson){return lesson.id=="fg:item:000001";})==1,
                    "Level1 base owner differs before finite selected replacement");
                items.erase(originalItem->id);for(const auto& variant:originalItem->variants)variants.erase(variant.id);catalog->lessons_.erase(originalItem);
            }
            for(const auto& lesson:added->lessons_){
                if(stop())return {};
                require(items.insert(lesson.id).second,"Selected extension item collides with installed catalog");
                for(const auto& variant:lesson.variants)require(variants.insert(variant.id).second,"Selected extension variant collides with installed catalog");
                catalog->lessons_.push_back(lesson);
                require(catalog->extensions_.emplace(lesson.id,added).second,"Duplicate selected extension owner");
            }
        }
        if(stop())return {};
        std::lock_guard<std::mutex> lock(stateMutex_);
        prepared_=std::move(catalog);preparedNames_=names;++revision_;
        observation.preparedOwners=preparedNames_;observation.revision=revision_;last_=observation;
        return prepared_;
    }catch(const content::LoadCanceled&){
        recordCanceled();
        return {};
    }catch(...){
        std::lock_guard<std::mutex> lock(stateMutex_);
        prepared_.reset();preparedNames_.clear();++revision_;
        observation.preparedOwners.clear();observation.revision=revision_;last_=observation;
        throw;
    }
}
}
