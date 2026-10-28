#pragma once
// Fixed QA access to the already compiled, hash-bound Level1 extension.
// No production target includes this helper. All validation/permission decisions
// are delegated to the unchanged Catalog loader; merge matches loadInstalled.
#include "content/LessonCatalog.hpp"
#include "content/InstalledExtensionRegistry.hpp"
#include <algorithm>
#include <stdexcept>
namespace fathom::lesson {
struct InstalledCatalogFixtureAccess final {
    static std::shared_ptr<const Catalog> levelOneWithControls(const std::filesystem::path& resources) {
        const auto require=[](bool ok,const char* reason){if(!ok)throw std::invalid_argument(reason);};
        const auto& registered=installedExtensionDescriptors();
        const auto found=std::find_if(registered.begin(),registered.end(),[](const auto& descriptor){return std::string(descriptor.directory)=="level001-extension";});
        require(found!=registered.end(),"Existing compiled Level1 descriptor missing");
        require(std::count_if(registered.begin(),registered.end(),[](const auto& descriptor){return std::string(descriptor.directory)=="level001-extension";})==1,"Compiled Level1 descriptor is not unique");
        const std::vector<InstalledExtensionDescriptor> descriptors{*found};
        const auto base=resources/"representative-controls";
        const std::vector<std::filesystem::path> installedExtensions{resources/"level001-extension"};
    const auto original=Catalog::load(base);auto catalog=std::shared_ptr<Catalog>(new Catalog(*original));
    std::set<std::string> items,variants;
    for(const auto& lesson:catalog->lessons_){items.insert(lesson.id);for(const auto& variant:lesson.variants)variants.insert(variant.id);}
    for(std::size_t i=0;i<installedExtensions.size();++i){
        require(!installedExtensions[i].empty(),"Installed extension path is missing");
        const auto added=Catalog::loadExtension(installedExtensions[i],descriptors[i]);
        if(std::string(descriptors[i].directory)=="level001-extension"){
            const auto originalItem=std::find_if(catalog->lessons_.begin(),catalog->lessons_.end(),
                [](const Lesson& lesson){return lesson.id=="fg:item:000001";});
            require(originalItem!=catalog->lessons_.end()&&
                std::count_if(catalog->lessons_.begin(),catalog->lessons_.end(),
                    [](const Lesson& lesson){return lesson.id=="fg:item:000001";})==1,
                "Level1 base owner differs before finite replacement");
            items.erase(originalItem->id);
            for(const auto& variant:originalItem->variants)variants.erase(variant.id);
            catalog->lessons_.erase(originalItem);
        }
        for(const auto& lesson:added->lessons_){
            require(items.insert(lesson.id).second,"Extension item collides with installed catalog");
            for(const auto& variant:lesson.variants)
                require(variants.insert(variant.id).second,"Extension variant collides with installed catalog");
            catalog->lessons_.push_back(lesson);
            require(catalog->extensions_.emplace(lesson.id,added).second,"Duplicate extension owner");
        }
    }
    return catalog;
    }
};
}
