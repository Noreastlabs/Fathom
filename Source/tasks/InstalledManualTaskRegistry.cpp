#include "tasks/InstalledManualTaskRegistry.hpp"
#include "tasks/GeneratedRepresentative.hpp"
#include "content/Canonical.hpp"
#include <stdexcept>

#ifndef FATHOM_TYPED_MANUAL_MANIFEST_SHA
#error Typed manual task manifest must be bound by CMake
#endif
#ifndef FATHOM_COMPILED_MANUAL_MANIFEST_SHA
#error Compiled manual family manifest must be bound by CMake
#endif
#ifndef FATHOM_COMPILED_MANUAL_TABLE_SHA
#error Compiled manual source table must be bound by CMake
#endif

namespace fathom::tasks {
namespace {
const json::Value& at(const json::Value& value,const char* key){return value.object().at(key);}
void need(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
}
InstalledManualTaskRegistry InstalledManualTaskRegistry::load(const std::filesystem::path& directory){
    InstalledManualTaskRegistry registry;
    try{
        const auto manifestBytes=content::readBounded(directory/"manifest.json",65536);
        need(content::sha256(manifestBytes)==FATHOM_TYPED_MANUAL_MANIFEST_SHA,"Typed manual manifest differs from reviewed version");
        const auto manifest=json::parse(manifestBytes);
        need(at(manifest,"schema").string()=="fathom.typed-manual-tasks.1","Typed manual manifest schema differs");
        need(at(manifest,"source_key").string()==generated::sourceKey,"Typed manual source key differs");
        need(at(manifest,"policy_sha256").string()==generated::policySha256,"Typed manual policy differs");
        need(at(manifest,"definition_path").string()=="level053-moduleb-cmajrp/task-definition.json","Typed manual definition path differs");
        need(at(manifest,"source_txt_sha256").string()=="eeedc261db89d3421fafc116e7352bbf8a3e3f6b7eddfd822ed6e4c731e0538e"&&
             at(manifest,"source_pdf_sha256").string()=="5e016f98623dc4362b2e3fc9b2d1cf1fb6c8692d6312d5b30a65234d47fa20ae","Typed manual source pins differ");
        const auto sourceBundle=directory.parent_path()/"source-library/bundle/assets/Notes/music/guitar project";
        const auto stem="Guitar_Exercises_Section_VI_Level_53_Major_and_Minor_Triads_Across_Four_Adjacent_Three_String_Sets";
        const auto sourceTxt=sourceBundle/"TXT version"/(std::string{stem}+".txt");
        const auto sourcePdf=sourceBundle/"PDF version"/(std::string{stem}+".pdf");
        need(content::sha256(content::readBounded(sourceTxt,65536))==at(manifest,"source_txt_sha256").string()&&
             content::sha256(content::readBounded(sourcePdf,131072))==at(manifest,"source_pdf_sha256").string(),
             "Packaged Level53 source TXT/PDF differs from reviewed bytes");
        need(at(manifest,"generated_header_sha256").string()=="eaa91d9d506c65d7ad1c30a654d80326b99c72b352ecb382bc7bec428df95eb6","Typed manual generated definition pin differs");
        need(at(manifest,"runtime_candidate").boolean()&&!at(manifest,"practice_admitted").boolean()&&
             !at(manifest,"official_child_accepted").boolean(),"Typed manual status differs");
        const auto definitionBytes=content::readBounded(directory/"level053-moduleb-cmajrp/task-definition.json",65536);
        need(content::sha256(definitionBytes)==at(manifest,"definition_sha256").string(),"Typed manual definition bytes differ");
        const auto definition=json::parse(definitionBytes);
        need(at(definition,"source_key").string()==generated::sourceKey&&
             at(definition,"policy_sha256").string()==generated::policySha256,"Typed manual definition identity differs");
        need(at(definition,"initial_bpm").null()&&at(definition,"initial_mode").string()=="unselected"&&
             at(definition,"audio_contract").null()&&!at(definition,"runtime_admitted").boolean()&&
             !at(definition,"official_accepted").boolean(),"Typed manual noncredit scope differs");
        (void)representativeDefinition(generated::sourceKey);
        registry.ready_=true;
    }catch(const std::exception& e){registry.error_=e.what();}
    // The legacy representative and a new compiled closure fail independently.
    // An invalid optional family cannot grant keys or disable a valid legacy key.
    try{
        const auto familyDirectory=directory.parent_path()/"compiled-manual-families-v1";
        const auto bytes=content::readBounded(familyDirectory/"manifest.json",65536);
        need(content::sha256(bytes)==FATHOM_COMPILED_MANUAL_MANIFEST_SHA,"Compiled manual family manifest differs");
        const auto manifest=json::parse(bytes);
        need(at(manifest,"schema").string()=="fathom.compiled-manual-family.1","Compiled manual schema differs");
        need(at(manifest,"generated_table_sha256").string()==FATHOM_COMPILED_MANUAL_TABLE_SHA,"Compiled native table binding differs");
        need(at(manifest,"definition_path").string()=="definitions.jsonl"&&at(manifest,"closure_path").string()=="family-closure.json","Compiled data paths differ");
        need(at(manifest,"runtime_candidate").boolean()&&!at(manifest,"practice_admitted").boolean()&&
             !at(manifest,"official_child_accepted").boolean(),"Compiled guidance candidate scope differs");
        const auto definitions=content::readBounded(familyDirectory/"definitions.jsonl",2*1024*1024);
        const auto closureBytes=content::readBounded(familyDirectory/"family-closure.json",65536);
        need(content::sha256(definitions)==at(manifest,"definitions_sha256").string()&&
             content::sha256(closureBytes)==at(manifest,"closure_sha256").string(),"Compiled data bytes differ");
        const auto closure=json::parse(closureBytes);
        need(at(closure,"source_clock").null()&&at(closure,"source_acoustic_gates").null()&&
             !at(closure,"runtime_admitted").boolean()&&!at(closure,"official_accepted").boolean(),"Compiled source/noncredit scope differs");
        const auto assets=directory.parent_path()/"source-library/bundle/assets";
        for(const auto& pin:at(closure,"source_pins").array()){
            const auto path=at(pin,"path").string();
            if(path.rfind("Notes/",0)==0){
                need(path.find("..") == std::string::npos,"Compiled source path is unsafe");
                need(content::sha256(content::readBounded(assets/path,256*1024))==at(pin,"sha256").string(),"Compiled packaged source differs");
            }
        }
        const auto& keys=at(manifest,"source_keys").array();need(keys.size()==compiledFamilyKeys().size(),"Compiled key denominator differs");
        for(std::size_t n=0;n<keys.size();++n){
            need(keys[n].string()==compiledFamilyKeys()[n],"Compiled exact source key differs");
            (void)compiledFamilyDefinition(keys[n].string());
        }
        registry.familyReady_=true;
    }catch(const std::exception& e){if(registry.error_.empty())registry.error_=e.what();}
    return registry;
}
bool InstalledManualTaskRegistry::contains(const std::string& sourceIdentity) const noexcept {
    if(ready_&&sourceIdentity=="level053/moduleb/p003-t1-r1-c2/cmajrp")return true;
    if(!familyReady_)return false;
    constexpr char prefix[]="exercise-completeness-r01/";
    constexpr std::size_t prefixLength=sizeof(prefix)-1;
    for(const auto& key:compiledFamilyKeys())
        if(key.size()>prefixLength&&key.compare(prefixLength,std::string::npos,sourceIdentity)==0)return true;
    return false;
}
std::optional<Definition> InstalledManualTaskRegistry::definition(const std::string& sourceIdentity) const {
    if(!contains(sourceIdentity))return std::nullopt;
    if(ready_&&sourceIdentity=="level053/moduleb/p003-t1-r1-c2/cmajrp")return representativeDefinition(generated::sourceKey);
    return compiledFamilyDefinition("exercise-completeness-r01/"+sourceIdentity);
}
}
