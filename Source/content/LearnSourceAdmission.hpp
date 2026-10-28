#pragma once
#include "content/LearnSourceIndex.hpp"
#include "content/ExerciseQueueCatalog.hpp"
namespace fathom::learn {
inline std::vector<navigation::AdmissionIdentity> choices(const Exercise& exercise,const lesson::Catalog& catalog){
    std::vector<navigation::AdmissionIdentity> result;
    for(const auto& binding:exercise.bindings)if(binding.exact)for(const auto& variant:binding.variants){
        try{
            auto admission=catalog.admit(binding.itemId,variant);
            if(!admission||admission->identity().object().at("package_sha256").string()!=binding.packageHash)continue;
            result.push_back(navigation::snapshotAdmission(*admission));
        }catch(const std::exception&){} // Retained source row stays unavailable; no replacement.
    }
    return result;
}
inline std::string availability(const Exercise& exercise,const lesson::Catalog& catalog){
    if(!choices(exercise,catalog).empty())return "Available for exact exercise Practice";
    if(std::any_of(exercise.bindings.begin(),exercise.bindings.end(),[&](const auto& b){
        if(!b.supplemental||b.exact)return false;
        try {auto admission=catalog.admit(b.itemId,b.variants.front());
            return admission&&admission->practiceAllowed()&&
                admission->identity().object().at("package_sha256").string()==b.packageHash;
        } catch(const std::exception&) {return false;}
    }))return "Supplemental Fathom-authored example available for inspection; original source exercise remains incomplete for exact Practice";
    if(std::any_of(exercise.bindings.begin(),exercise.bindings.end(),[](const auto& b){return !b.exact;}))return "Covered by larger case; exact exercise unavailable";
    return "Not yet available for Practice";
}
}
