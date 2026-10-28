#include "content/CleanRuntimeEnvelope.hpp"
#include "content/LessonCatalog.hpp"
#include "content/InstalledExtensionRegistry.hpp"
#include <algorithm>
#include <map>
#include <set>
#include <sstream>

namespace fathom::lesson {
namespace {
using J=json::Value;
const J& at(const J& j,const std::string& k){return j.object().at(k);}
void require(bool ok,const std::string& message){if(!ok)throw std::runtime_error(message);}
std::int64_t integer(const J& j){std::int64_t n=0;require(j.integer(n),"Expected whole-number manifest value");return n;}
void noDots(const std::filesystem::path& p){for(const auto& c:p)require(c!="."&&c!="..","Dot paths are not supported; use the installed bundle path");}
std::filesystem::path safeFile(const std::filesystem::path& root,const std::string& name){
    require(!name.empty()&&name.find('\0')==std::string::npos&&name.find('\\')==std::string::npos,"Invalid lesson asset path");
    const std::filesystem::path rel(name);require(!rel.is_absolute()&&!rel.has_root_name(),"Lesson asset must be relative to its bundle");noDots(rel);
    auto file=root;for(const auto& part:rel){file/=part;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(file)),"Lesson bundle symlinks are not supported: "+name);}
    require(std::filesystem::is_regular_file(file),"Missing local lesson asset: "+name);return file;
}
std::string humanKey(std::string s){std::replace(s.begin(),s.end(),'_',' ');return s;}
std::string display(const J& j,int depth=0){
    const std::string pad(static_cast<std::size_t>(depth)*2,' ');std::string out;
    if(j.isObject()){for(const auto& kv:j.object()){
        if(kv.first=="anchors"&&kv.second.isArray()){
            out+=pad+"Score anchors:\n";std::size_t score=0;
            for(const auto& anchor:kv.second.array())out+=pad+"  "+std::to_string(score++)+" = "+display(anchor)+"\n";
        }else out+=pad+humanKey(kv.first)+": "+(kv.second.isObject()||kv.second.isArray()?"\n"+display(kv.second,depth+1):display(kv.second))+"\n";
    }}
    else if(j.isArray()){for(const auto& v:j.array())out+=pad+"- "+display(v,depth+1)+"\n";}
    else if(j.isString())out=j.string();else if(j.null())out="Not supplied";else if(j.isBool())out=j.boolean()?"Yes":"No";else out=json::stringify(j);
    return out;
}
}
std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& input,
    const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    require(input.is_absolute(),"Choose an absolute local lesson bundle path");noDots(input);
    auto part=std::filesystem::path{};for(const auto& c:input){part/=c;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(part)),"Lesson bundle root must not pass through a symlink");}
    require(std::filesystem::is_directory(input),"Lesson bundle is missing; rebuild or reinstall this preview with its local resources");
    const auto root=std::filesystem::canonical(input);
    const auto transport=content::CleanRuntimeEnvelope::open(root,FATHOM_LESSON_MANIFEST_SHA,"manifest.json",canceled);
    const auto manifestBytes=content::readBounded(safeFile(root,"manifest.json"),1024*1024,canceled);
    require(content::sha256(manifestBytes)==FATHOM_LESSON_MANIFEST_SHA,"Unsupported or changed lesson manifest; use the bundle supplied with this app version");
    const auto manifest=json::parse(manifestBytes);
    checkpoint();
    require(at(manifest,"version").string()=="lesson-bundle.1","Unsupported lesson bundle version");
    std::map<std::string,std::string> bytes;std::uint64_t total=0;
    for(const auto& file:at(manifest,"files").array()){
        checkpoint();
        const auto name=at(file,"path").string();const auto size=integer(at(file,"bytes"));
        if(transport->hasArchivedEvidence(name)){
            require(size>=0,"Archived asset size invalid");
            transport->verifyArchivedEvidence(name,at(file,"sha256").string(),static_cast<std::size_t>(size));continue;
        }
        require(size>=0&&size<=32*1024*1024,"Lesson asset exceeds supported size");total+=static_cast<std::uint64_t>(size);require(total<=64*1024*1024,"Lesson bundle exceeds supported total size");
        const auto actual=content::readBounded(safeFile(root,name),static_cast<std::size_t>(size),canceled);
        require(actual.size()==static_cast<std::size_t>(size)&&content::sha256(actual)==at(file,"sha256").string(),"Changed or incomplete lesson asset: "+name);
        require(bytes.emplace(name,actual).second,"Duplicate lesson asset: "+name);
        checkpoint();
    }
    const auto& entries=at(manifest,"entries");auto entry=[&](const char* name)->const std::string&{return bytes.at(at(entries,name).string());};
    const auto profile=json::parse(entry("profile"));const auto decision=json::parse(entry("decision"));
    checkpoint();
    require(at(decision,"status").string()=="ACCEPTED"&&at(decision,"version").string()=="converted-controls-admission-decision.1","Converted control decision is not accepted/supported");
    require(at(decision,"package").string()==content::sha256(entry("package"))&&at(decision,"expectedProfile").string()==content::sha256(entry("profile")),"Accepted decision does not bind this package/profile");
    require(!at(decision,"applicationPlaybackAuthorized").boolean(),"Reader requires the unchanged bounded source decision, not an unreviewed playback flag");
    auto result=content::validate({entry("package"),entry("registry"),entry("profile"),at(decision,"expectedProfile").string(),root,canceled,transport});
    checkpoint();
    require(result.validReference&&result.exitCode==2,"Local lesson validation failed; reinstall the matching complete bundle (details available in developer validation)");
    auto catalog=std::shared_ptr<Catalog>(new Catalog);catalog->package_=json::parse(entry("package"));catalog->validation_=std::move(result.report);
    catalog->transportHash_=transport->transportSha();catalog->manifestHash_=content::sha256(manifestBytes);catalog->decisionHash_=content::sha256(entry("decision"));catalog->packageHash_=content::sha256(entry("package"));
    catalog->contentVersion_=at(catalog->package_,"content_version").string();
    require(catalog->contentVersion_==at(manifest,"content_version").string()&&catalog->contentVersion_==at(decision,"contentVersion").string(),"Content version mismatch");
    const auto& resourceBinding=at(profile,"resource_plan");catalog->resources_=json::parse(bytes.at(at(resourceBinding,"path").string()));
    std::set<std::string> resourceIds;for(const auto& resource:at(catalog->resources_,"resources").array()){
        require(at(resource,"availability").string()=="required_unsupplied"&&at(resource,"supplied_asset").null()&&at(resource,"rights_evidence").null(),"Resource availability changed without task evidence");
        require(resourceIds.insert(at(resource,"id").string()).second,"Duplicate resource ID");
    }
    std::set<std::string> expectedResources;for(const auto& id:at(at(decision,"resources"),"entry_ids").array())expectedResources.insert(id.string());
    require(resourceIds==expectedResources&&resourceIds.size()==16,"Required resource plan coverage differs");
    std::map<std::string,const J*> decisions;for(const auto& v:at(decision,"variants").array())require(decisions.emplace(at(v,"variantId").string(),&v).second,"Duplicate decision variant");
    std::map<std::string,const J*> reports;for(const auto& report:at(catalog->validation_,"variants").array())
        require(reports.emplace(at(report,"variant_id").string(),&report).second,"Duplicate validator variant");
    std::map<std::string,const content::VariantResult*> variants;for(const auto& v:result.variants)require(variants.emplace(v.id,&v).second,"Duplicate projected variant");
    std::set<std::string> consumed,items;
    for(const auto& record:at(catalog->package_,"records").array()){
        checkpoint();
        Lesson lesson;lesson.id=at(record,"id").string();lesson.title=at(record,"title").string();lesson.level=static_cast<int>(integer(at(record,"legacy_level")));lesson.record=record;
        require(items.insert(lesson.id).second,"Duplicate lesson identity");
        for(const auto& authored:at(record,"variants").array()){
            checkpoint();
            Variant v;v.id=at(authored,"id").string();v.label=at(authored,"label").string();v.authored=authored;
            const auto& projected=*variants.at(v.id);const auto& d=*decisions.at(v.id);
            require(consumed.insert(v.id).second&&projected.itemId==lesson.id&&at(d,"itemId").string()==lesson.id,"Variant owner differs from accepted source");
            require(projected.validation.validReference()&&at(d,"validReference").boolean(),"Variant reference is invalid");
            require(projected.bindingsComplete==at(d,"bindingsComplete").boolean()&&projected.readiness.technicallyRenderable==at(d,"technicallyRenderable").boolean(),"Variant capability differs from reviewed decision");
            require(!at(d,"applicationPlaybackAuthorized").boolean(),"Unexpected playback authorization");
            v.model=projected.validation.model;v.technicallyRenderable=projected.readiness.technicallyRenderable;
            std::set<std::string> issues;J::Array issueCodes;
            for(const auto& issue:at(*reports.at(v.id),"issues").array()){
                const auto code=at(issue,"code").string();issueCodes.emplace_back(code);
                if(code!="not_admitted")issues.insert(at(issue,"message").string());
            }
            if(J(issueCodes)!=at(d,"issueCodes")){
                // This one historical decision predates native SlideArrival support.
                // The accepted bundle and decision are immutable; only the exact
                // observed diagnostic deletion is compatible with this reader.
                const auto& variantReport=*reports.at(v.id);
                const auto& currentIssues=at(variantReport,"issues").array();
                const auto issueAt=[&](std::size_t index,const char* code,
                                      const std::string& event,const char* field){
                    const auto& issue=currentIssues[index];
                    return at(issue,"code").string()==code&&at(issue,"event").string()==event&&
                           at(issue,"field").string()==field;
                };
                const bool compatible=
                    catalog->manifestHash_=="f57b3c6e1adddd3699bb27c8c0c35f356fbbcb2808f409f87bcca531afa75a8e"&&
                    at(manifest,"version").string()=="lesson-bundle.1"&&
                    at(manifest,"content_version").string()=="representative-controls.1"&&
                    catalog->contentVersion_=="representative-controls.1"&&
                    catalog->packageHash_=="0ecd2b1466a7b16e10ca6221299b3b1b21c197ff13cd5df9f038e307673aea8b"&&
                    catalog->decisionHash_=="e10359bfabf8d0c481447c592a62fe8c2d255f3bebb85d9b5872552447ae4164"&&
                    lesson.id=="fg:item:000007"&&v.id=="fg:variant:000040"&&
                    at(decision,"variants").array().size()==49&&reports.size()==49&&variants.size()==49&&
                    at(d,"issueCodes")==json::parse(R"(["unresolved_scope","unresolved_scope","unresolved_scope","unresolved_scope","unsupported_technique","unsupported_technique","unsupported_technique","unsupported_technique","unsupported_technique","not_admitted"])")&&
                    J(issueCodes)==json::parse(R"(["unresolved_scope","unresolved_scope","unresolved_scope","unresolved_scope","not_admitted"])")&&
                    currentIssues.size()==5&&
                    issueAt(0,"unresolved_scope","fg:item:000007:event:0003","scopeStrings")&&
                    issueAt(1,"unresolved_scope","fg:item:000007:event:0008","scopeStrings")&&
                    issueAt(2,"unresolved_scope","fg:item:000007:event:0011","scopeStrings")&&
                    issueAt(3,"unresolved_scope","fg:item:000007:event:0016","scopeStrings")&&
                    issueAt(4,"not_admitted","","admission")&&
                    result.validReference&&result.exitCode==2&&
                    at(catalog->validation_,"valid_reference").boolean()&&
                    integer(at(catalog->validation_,"exit_code"))==2&&
                    !at(catalog->validation_,"curriculum_playback_authorized").boolean()&&
                    projected.validation.validReference()&&projected.bindingsComplete&&
                    !projected.readiness.technicallyRenderable&&
                    at(d,"validReference").boolean()&&at(d,"bindingsComplete").boolean()&&
                    !at(d,"technicallyRenderable").boolean()&&
                    !at(d,"applicationPlaybackAuthorized").boolean()&&
                    !at(decision,"applicationPlaybackAuthorized").boolean()&&
                    !at(variantReport,"curriculum_playback_authorized").boolean()&&
                    !at(variantReport,"technically_renderable").boolean()&&
                    at(variantReport,"bindings_complete").boolean()&&
                    at(variantReport,"valid_reference").boolean();
                require(compatible,"Variant diagnostics differ from accepted decision");
            }
            if(!projected.bindingsComplete){
                if(const auto* accent=authored.find("accent_policy");accent&&accent->string()=="after_crossing")issues.insert("The authored "+accent->string()+" accent operation is not supported by this reference renderer.");
                if(const auto* pause=authored.find("tail_pause");pause&&!pause->null())issues.insert("The authored tail pause is retained as an instruction; this projection cannot execute that pause operation.");
            }
            v.limitations.assign(issues.begin(),issues.end());lesson.variants.push_back(std::move(v));
        }
        for(const auto& resource:at(catalog->resources_,"resources").array())if(integer(at(resource,"level"))==lesson.level)lesson.resources.push_back(resource);
        catalog->lessons_.push_back(std::move(lesson));
    }
    require(consumed.size()==variants.size()&&consumed.size()==decisions.size()&&
            consumed.size()==reports.size(),"Variant coverage mismatch");
    // Registry/content order is retained; titles and numeric level are not identity.
    checkpoint();
    return catalog;
}
std::vector<std::string> Catalog::installedExtensionDirectoryNames(){
    std::vector<std::string> names;
    for(const auto& descriptor:installedExtensionDescriptors())names.emplace_back(descriptor.directory);
    return names;
}
Catalog::BundleIdentity Catalog::reverifyBundle(const std::filesystem::path& input,
    const InstalledExtensionDescriptor* descriptor,const json::Value& validation,
    const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    require(input.is_absolute(),"Choose an absolute local lesson bundle path");noDots(input);
    auto part=std::filesystem::path{};
    for(const auto& c:input){part/=c;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(part)),"Lesson bundle root must not pass through a symlink");}
    require(std::filesystem::is_directory(input),"Requested lesson bundle is missing; reinstall the complete app");
    const auto root=std::filesystem::canonical(input);
    const auto transport=content::CleanRuntimeEnvelope::open(root,(descriptor?descriptor->manifestSha256:FATHOM_LESSON_MANIFEST_SHA),"manifest.json",canceled);
    const auto manifestBytes=content::readBounded(safeFile(root,"manifest.json"),1024*1024,canceled);
    BundleIdentity identity;identity.transportHash=transport->transportSha();
    identity.manifestHash=content::sha256(manifestBytes);
    require(identity.manifestHash==(descriptor?descriptor->manifestSha256:FATHOM_LESSON_MANIFEST_SHA),
        "Unsupported or changed requested lesson manifest");
    const auto manifest=json::parse(manifestBytes);
    require(at(manifest,"version").string()==(descriptor?descriptor->bundleVersion:"lesson-bundle.1"),
        "Unsupported requested lesson bundle version");
    const auto packageName=at(at(manifest,"entries"),"package").string();
    std::set<std::string> installedFiles{"manifest.json"};
    std::map<std::string,std::string> checkedPaths;
    std::uint64_t total=0;
    for(const auto& file:at(manifest,"files").array()){
        checkpoint();
        const auto name=at(file,"path").string();const auto size=integer(at(file,"bytes"));
        if(transport->hasArchivedEvidence(name)){
            require(size>=0,"Archived asset size invalid");
            transport->verifyArchivedEvidence(name,at(file,"sha256").string(),static_cast<std::size_t>(size));continue;
        }
        require(size>=0&&size<=32*1024*1024,"Requested lesson asset exceeds supported size");
        total+=static_cast<std::uint64_t>(size);require(total<=64*1024*1024,"Requested lesson bundle exceeds supported total size");
        const auto bytes=content::readBounded(safeFile(root,name),static_cast<std::size_t>(size),canceled);
        const auto hash=content::sha256(bytes);
        require(bytes.size()==static_cast<std::size_t>(size)&&hash==at(file,"sha256").string(),
            "Changed or incomplete requested lesson asset: "+name);
        require(installedFiles.insert(name).second,"Duplicate requested lesson asset: "+name);
        checkedPaths.emplace((root/name).string(),hash);
        if(name==packageName)identity.packageHash=hash;
        ++identity.assetCount;identity.assetBytes+=bytes.size();
        checkpoint();
    }
    require(!identity.packageHash.empty(),"Requested lesson package is absent from its manifest");
    // Re-resolve Canonical's recorded source requests too. In the base bundle,
    // a newly present historical Results alias must not bypass the old fallback
    // binding merely because all manifest-listed primary files are unchanged.
    const auto withinRoot=[&](const std::filesystem::path& candidate){
        auto a=root.begin(),b=candidate.begin();
        for(;a!=root.end();++a,++b)require(b!=candidate.end()&&*a==*b,"Cached source resolution escapes its installed root");
    };
    for(const auto& asset:at(validation,"source_assets").array()){
        checkpoint();
        const auto relative=at(asset,"path").string();
        require(!relative.empty()&&relative.find('\0')==std::string::npos&&relative.find('\\')==std::string::npos,"Invalid cached source asset path");
        const std::filesystem::path rel(relative);
        require(!rel.is_absolute()&&!rel.has_root_name(),"Cached source asset must remain relative");noDots(rel);
        std::error_code ec;const auto requested=root/rel;auto selected=requested;
        const auto status=std::filesystem::symlink_status(requested,ec);
        require(!ec||ec==std::make_error_code(std::errc::no_such_file_or_directory),"Cached source path cannot be inspected");
        if(status.type()==std::filesystem::file_type::not_found){
            ec.clear();const auto prospective=std::filesystem::weakly_canonical(requested,ec);
            require(!ec,"Cached source path cannot be resolved");withinRoot(prospective);
            const auto suffix=rel.lexically_relative("Results");
            if(relative.rfind("Results/",0)==0&&relative.rfind("Results/primary/",0)!=0&&!suffix.empty()&&suffix!=".")selected=root/"Results/primary"/suffix;
        }
        ec.clear();const auto resolved=std::filesystem::canonical(selected,ec);
        require(!ec,"Cached source asset cannot be resolved");withinRoot(resolved);
        require(std::filesystem::is_regular_file(resolved),"Cached source asset is not a regular file");
        const auto expected=at(asset,"sha256").string();const auto found=checkedPaths.find(resolved.string());
        if(found!=checkedPaths.end())require(found->second==expected,"Cached source hash differs from its current manifest identity");
        else{
            const auto bytes=content::readBounded(resolved,32*1024*1024,canceled);const auto hash=content::sha256(bytes);
            require(hash==expected,"Changed cached source asset: "+relative);
            checkedPaths.emplace(resolved.string(),hash);++identity.assetCount;identity.assetBytes+=bytes.size();
        }
    }
    // Match the existing extension loader's closed file-set contract. The base
    // reader has always allowed unrelated unreferenced files; retain that rule.
    if(descriptor){
        for(const auto& file:std::filesystem::recursive_directory_iterator(root)){
            checkpoint();
            const auto rel=file.path().lexically_relative(root).generic_string();
            require(!std::filesystem::is_symlink(file.symlink_status()),"Extension symlink is not supported: "+rel);
            if(file.is_regular_file())require(installedFiles.erase(rel)==1,"Unexpected extension asset: "+rel);
            else require(file.is_directory(),"Unexpected extension entry: "+rel);
        }
        require(installedFiles.empty(),"Incomplete requested extension file set");
    }
    checkpoint();
    return identity;
}
std::shared_ptr<const Catalog> Catalog::loadExtension(const std::filesystem::path& input,
    const InstalledExtensionDescriptor& descriptor,const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    require(input.is_absolute(),"Choose an absolute extension bundle path");noDots(input);
    auto part=std::filesystem::path{};
    for(const auto& c:input){part/=c;require(!std::filesystem::is_symlink(std::filesystem::symlink_status(part)),"Extension root must not pass through a symlink");}
    require(std::filesystem::is_directory(input),std::string(descriptor.directory)+" is missing; reinstall the complete app");
    const auto root=std::filesystem::canonical(input);
    const auto transport=content::CleanRuntimeEnvelope::open(root,descriptor.manifestSha256,"manifest.json",canceled);
    const auto manifestBytes=content::readBounded(safeFile(root,"manifest.json"),1024*1024,canceled);
    require(content::sha256(manifestBytes)==descriptor.manifestSha256,"Unsupported or changed installed extension manifest");
    const auto manifest=json::parse(manifestBytes);
    require(at(manifest,"version").string()==descriptor.bundleVersion,"Unsupported installed extension bundle version");
    std::map<std::string,std::string> bytes;std::set<std::string> installedFiles{"manifest.json"};
    std::uint64_t total=0;
    for(const auto& file:at(manifest,"files").array()){
        checkpoint();
        const auto name=at(file,"path").string();const auto size=integer(at(file,"bytes"));
        if(transport->hasArchivedEvidence(name)){
            require(size>=0,"Archived asset size invalid");
            transport->verifyArchivedEvidence(name,at(file,"sha256").string(),static_cast<std::size_t>(size));continue;
        }
        require(size>=0&&size<=32*1024*1024,"Extension asset exceeds supported size");
        total+=static_cast<std::uint64_t>(size);require(total<=64*1024*1024,"Extension exceeds supported total size");
        const auto actual=content::readBounded(safeFile(root,name),static_cast<std::size_t>(size),canceled);
        require(actual.size()==static_cast<std::size_t>(size)&&content::sha256(actual)==at(file,"sha256").string(),"Changed or incomplete extension asset: "+name);
        require(bytes.emplace(name,actual).second&&installedFiles.insert(name).second,"Duplicate extension asset: "+name);
        checkpoint();
    }
    for(const auto& file:std::filesystem::recursive_directory_iterator(root)){
        checkpoint();
        const auto rel=file.path().lexically_relative(root).generic_string();
        require(!std::filesystem::is_symlink(file.symlink_status()),"Extension symlink is not supported: "+rel);
        if(file.is_regular_file())require(installedFiles.erase(rel)==1,"Unexpected extension asset: "+rel);
        else require(file.is_directory(),"Unexpected extension entry: "+rel);
    }
    require(installedFiles.empty(),"Incomplete installed extension file set");
    const auto& entries=at(manifest,"entries");
    auto entry=[&](const char* name)->const std::string&{return bytes.at(at(entries,name).string());};
    const std::string provenance=descriptor.hasProvenance?entry("provenance"):std::string{};
    auto result=descriptor.validate({entry("package"),entry("registry"),entry("profile"),
        at(manifest,"profile_sha256").string(),root,canceled,transport},entry("decision"),
        at(manifest,"decision_sha256").string(),provenance);
    checkpoint();
    auto catalog=std::shared_ptr<Catalog>(new Catalog);
    catalog->package_=json::parse(entry("package"));catalog->validation_=std::move(result.report);
    catalog->transportHash_=transport->transportSha();catalog->manifestHash_=content::sha256(manifestBytes);
    catalog->decisionHash_=content::sha256(entry("decision"));
    catalog->packageHash_=content::sha256(entry("package"));
    catalog->contentVersion_=at(catalog->package_,"content_version").string();
    require(catalog->contentVersion_==at(manifest,"content_version").string(),"Extension content version mismatch");
    const auto profile=json::parse(entry("profile"));
    const bool fullLevel001=std::string(descriptor.directory)=="level001-extension";
    if(fullLevel001){
        require(at(profile,"resource_plan").null(),"Level1 frozen profile resource plan differs");
        const auto& planBytes=entry("empty_resource_plan");
        require(content::sha256(planBytes)=="bdf0f2424df0f72e0a8b32a225d8e42a07b5005baa0a7fa8f023ca62c9c5fbd4",
            "Level1 pinned empty resource plan differs");
        catalog->resources_=json::parse(planBytes);
        require(at(catalog->resources_,"resources").array().empty(),"Level1 resource plan must be empty");
    }else catalog->resources_=json::parse(bytes.at(at(at(profile,"resource_plan"),"path").string()));
    const auto& records=at(catalog->package_,"records").array();
    std::vector<InstalledExtensionCase> cases{{descriptor.item,descriptor.firstVariant,
        descriptor.secondVariant,descriptor.level,descriptor.stepNumerator,
        descriptor.stepDenominator,descriptor.eventCount,descriptor.description,
        descriptor.baseGapAfterEvent,descriptor.baseGapNumerator,
        descriptor.baseGapDenominator}};
    cases.insert(cases.end(),descriptor.additionalCases.begin(),descriptor.additionalCases.end());
    require(records.size()==cases.size(),"Installed extension case count differs from finite descriptor");
    std::set<std::string> allVariants;
    for(std::size_t index=0;index<cases.size();++index){
        checkpoint();
        const auto& record=records[index];const auto& selected=cases[index];
        Lesson lesson;lesson.id=at(record,"id").string();lesson.title=at(record,"title").string();
        lesson.level=static_cast<int>(integer(at(record,"legacy_level")));lesson.record=record;
        require(lesson.id==selected.item&&lesson.level==selected.level,
            "Installed extension identity/level differs");
        std::set<std::string> observedVariants;
        for(const auto& authored:at(record,"variants").array()){
            checkpoint();
            const auto id=at(authored,"id").string();
            const auto found=std::find_if(result.variants.begin(),result.variants.end(),
                [&](const auto& v){return v.id==id&&v.itemId==lesson.id;});
            require(found!=result.variants.end()&&observedVariants.insert(id).second&&
                allVariants.insert(id).second,"Missing, foreign or duplicate extension variant projection");
            Variant variant;variant.id=id;variant.label=at(authored,"label").string();variant.authored=authored;
            variant.model=found->validation.model;variant.technicallyRenderable=found->readiness.technicallyRenderable;
            lesson.variants.push_back(std::move(variant));
        }
        const bool single=descriptor.singleVariant&&index==0&&cases.size()==1;
        const std::set<std::string> expectedVariants=single
            ? std::set<std::string>{selected.firstVariant}
            : std::set<std::string>{selected.firstVariant,selected.secondVariant};
        std::set<std::string> expectedPresent=expectedVariants;
        if(fullLevel001){
            require(lesson.level==1&&at(record,"variants").array().size()==6,
                "Level1 installed item requires four historical and two full-route choices");
            for(std::size_t old=0;old<4;++old)
                expectedPresent.insert(at(at(record,"variants").array()[old],"id").string());
        }
        if(std::string(descriptor.directory)=="level003-modeb001-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000240"&&lesson.level==3&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:000827"&&
                std::string(selected.secondVariant)=="fg:variant:000829"&&
                exactLevel003ModeBRetainedVariants(at(record,"variants")),
                "Level3 ModeB001 retained-variant permission scope differs");
            for(int variant=826;variant<=837;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex002-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000445"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003287"&&
                std::string(selected.secondVariant)=="fg:variant:003289"&&
                exactLevel004Ex002RetainedVariants(at(record,"variants")),
                "Level4 Exercise002 retained-variant permission scope differs");
            for(int variant=3286;variant<=3297;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex003-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000446"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003299"&&
                std::string(selected.secondVariant)=="fg:variant:003301"&&
                exactLevel004Ex003RetainedVariants(at(record,"variants")),
                "Level4 Exercise003 retained-variant permission scope differs");
            for(int variant=3298;variant<=3309;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex004-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000447"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003311"&&
                std::string(selected.secondVariant)=="fg:variant:003313"&&
                exactLevel004Ex004RetainedVariants(at(record,"variants")),
                "Level4 Exercise004 retained-variant permission scope differs");
            for(int variant=3310;variant<=3321;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex005-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000448"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003323"&&
                std::string(selected.secondVariant)=="fg:variant:003325"&&
                exactLevel004Ex005RetainedVariants(at(record,"variants")),
                "Level4 Exercise005 retained-variant permission scope differs");
            for(int variant=3322;variant<=3333;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex006-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000449"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003335"&&
                std::string(selected.secondVariant)=="fg:variant:003337"&&
                exactLevel004Ex006RetainedVariants(at(record,"variants")),
                "Level4 Exercise006 retained-variant permission scope differs");
            for(int variant=3334;variant<=3345;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex007-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000450"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003347"&&
                std::string(selected.secondVariant)=="fg:variant:003349"&&
                exactLevel004Ex007RetainedVariants(at(record,"variants")),
                "Level4 Exercise007 retained-variant permission scope differs");
            for(int variant=3346;variant<=3357;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex008-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000451"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003359"&&
                std::string(selected.secondVariant)=="fg:variant:003361"&&
                exactLevel004Ex008RetainedVariants(at(record,"variants")),
                "Level4 Exercise008 retained-variant permission scope differs");
            for(int variant=3358;variant<=3369;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex009-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000452"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003371"&&
                std::string(selected.secondVariant)=="fg:variant:003373"&&
                exactLevel004Ex009RetainedVariants(at(record,"variants")),
                "Level4 Exercise009 retained-variant permission scope differs");
            for(int variant=3370;variant<=3381;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex010-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000453"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003383"&&
                std::string(selected.secondVariant)=="fg:variant:003385"&&
                exactLevel004Ex010RetainedVariants(at(record,"variants")),
                "Level4 Exercise010 retained-variant permission scope differs");
            for(int variant=3382;variant<=3393;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex011-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000454"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003395"&&
                std::string(selected.secondVariant)=="fg:variant:003397"&&
                exactLevel004Ex011RetainedVariants(at(record,"variants")),
                "Level4 Exercise011 retained-variant permission scope differs");
            for(int variant=3394;variant<=3405;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex012-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000455"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003407"&&
                std::string(selected.secondVariant)=="fg:variant:003409"&&
                exactLevel004Ex012RetainedVariants(at(record,"variants")),
                "Level4 Exercise012 retained-variant permission scope differs");
            for(int variant=3406;variant<=3417;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex013-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000456"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003419"&&
                std::string(selected.secondVariant)=="fg:variant:003421"&&
                exactLevel004Ex013RetainedVariants(at(record,"variants")),
                "Level4 Exercise013 retained-variant permission scope differs");
            for(int variant=3418;variant<=3429;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex014-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000457"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003431"&&
                std::string(selected.secondVariant)=="fg:variant:003433"&&
                exactLevel004Ex014RetainedVariants(at(record,"variants")),
                "Level4 Exercise014 retained-variant permission scope differs");
            for(int variant=3430;variant<=3441;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        if(std::string(descriptor.directory)=="level004-ex015-extension"){
            require(cases.size()==1&&index==0&&lesson.id=="fg:item:000458"&&lesson.level==4&&
                integer(at(record,"content_revision"))==1&&
                std::string(selected.firstVariant)=="fg:variant:003443"&&
                std::string(selected.secondVariant)=="fg:variant:003445"&&
                exactLevel004Ex015RetainedVariants(at(record,"variants")),
                "Level4 Exercise015 retained-variant permission scope differs");
            for(int variant=3442;variant<=3453;++variant){
                const auto digits=std::to_string(variant);
                expectedPresent.insert("fg:variant:"+std::string(6-digits.size(),'0')+digits);
            }
        }
        require((single ? (selected.secondVariant[0]=='\0'&&expectedVariants.size()==1)
                        : expectedVariants.size()==2)&&observedVariants==expectedPresent,
            "Installed extension variant coverage differs");
        require(validInstalledGaps(selected.eventCount,selected.gapAfterEvent,
            selected.gapNumerator,selected.gapDenominator,selected.secondGapAfterEvent,
            selected.secondGapNumerator,selected.secondGapDenominator),
            "Invalid mixed, unordered or out-of-range extension gap permission");
        const bool oneGap=selected.gapAfterEvent!=0;
        const bool twoGaps=selected.secondGapAfterEvent!=0;
        for(const auto& resource:at(catalog->resources_,"resources").array())
            if(integer(at(resource,"level"))==lesson.level)lesson.resources.push_back(resource);
        require(catalog->extensionPermissions_.emplace(lesson.id,
            ExtensionPermission{expectedVariants,Rational{selected.stepNumerator,selected.stepDenominator},
                selected.eventCount,selected.description,selected.gapAfterEvent,
                oneGap?Rational{selected.gapNumerator,selected.gapDenominator}:Rational{0},
                selected.secondGapAfterEvent,
                twoGaps?Rational{selected.secondGapNumerator,selected.secondGapDenominator}:Rational{0}}).second,
            "Duplicate installed extension permission");
        catalog->lessons_.push_back(std::move(lesson));
    }
    require(result.records.size()==cases.size()&&result.variants.size()==allVariants.size(),
        "Installed extension native case or variant coverage differs");
    checkpoint();
    return catalog;
}
std::shared_ptr<const Catalog> Catalog::loadInstalled(const std::filesystem::path& base,
    const std::vector<std::filesystem::path>& installedExtensions,
    const content::CancellationCheck& canceled){
    const auto checkpoint=[&]{content::checkLoadCanceled(canceled);};
    checkpoint();
    const auto& descriptors=installedExtensionDescriptors();
    require(installedExtensions.size()<=descriptors.size(),"Unknown installed extension was supplied");
    const auto original=load(base,canceled);checkpoint();auto catalog=std::shared_ptr<Catalog>(new Catalog(*original));
    std::set<std::string> items,variants;
    for(const auto& lesson:catalog->lessons_){items.insert(lesson.id);for(const auto& variant:lesson.variants)variants.insert(variant.id);}
    for(std::size_t i=0;i<installedExtensions.size();++i){
        checkpoint();
        require(!installedExtensions[i].empty(),"Installed extension path is missing");
        const auto added=loadExtension(installedExtensions[i],descriptors[i],canceled);
        checkpoint();
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
            checkpoint();
            require(items.insert(lesson.id).second,"Extension item collides with installed catalog");
            for(const auto& variant:lesson.variants)
                require(variants.insert(variant.id).second,"Extension variant collides with installed catalog");
            catalog->lessons_.push_back(lesson);
            require(catalog->extensions_.emplace(lesson.id,added).second,"Duplicate extension owner");
        }
    }
    checkpoint();
    return catalog;
}
std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& base,const std::filesystem::path& rung02){
    return loadInstalled(base,{rung02});
}
std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& base,const std::filesystem::path& rung02,
    const std::filesystem::path& rung03){return loadInstalled(base,{rung02,rung03});}
std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& base,const std::filesystem::path& rung02,
    const std::filesystem::path& rung03,const std::filesystem::path& rung04){
    return loadInstalled(base,{rung02,rung03,rung04});
}
std::shared_ptr<const Catalog> Catalog::load(const std::filesystem::path& base,const std::filesystem::path& rung02,
    const std::filesystem::path& rung03,const std::filesystem::path& rung04,const std::filesystem::path& level006){
    return loadInstalled(base,{rung02,rung03,rung04,level006});
}
const std::string& Catalog::contentVersion(const std::string& item) const {
    lesson(item);
    const auto owner=extensions_.find(item);
    return owner==extensions_.end()?contentVersion_:owner->second->contentVersion_;
}
std::size_t Catalog::sourceEntryCount() const {
    std::size_t count=at(package_,"sources").object().size();
    std::set<const Catalog*> counted;
    for(const auto& owner:extensions_)
        if(counted.insert(owner.second.get()).second)count+=owner.second->sourceEntryCount();
    return count;
}
const Lesson& Catalog::lesson(const std::string& id) const {for(const auto& l:lessons_)if(l.id==id)return l;throw std::out_of_range("This lesson identity is not in the loaded version");}
const Variant& Catalog::variant(const std::string& item,const std::string& id) const {for(const auto& v:lesson(item).variants)if(v.id==id)return v;throw std::out_of_range("This variant does not belong to the selected lesson");}
std::shared_ptr<const Admission> Catalog::admit(const std::string& item,const std::string& id) const {
    const auto owner=extensions_.find(item);
    if(owner!=extensions_.end())return owner->second->admit(item,id);
    const auto& l=lesson(item);const auto& v=variant(item,id);
    require(v.technicallyRenderable,"Reference unavailable for this variant. "+readinessText(v));
    const bool l3=item=="fg:item:000002"&&(id=="fg:variant:000006"||id=="fg:variant:000008"||id=="fg:variant:000010"||id=="fg:variant:000012");
    const bool l12=item=="fg:item:000003"&&(id=="fg:variant:000029"||id=="fg:variant:000030");
    const bool triplet=item=="fg:item:000004"&&(id=="fg:variant:000033"||id=="fg:variant:000034");
    const bool sextuplet=item=="fg:item:000004"&&(id=="fg:variant:000035"||id=="fg:variant:000036");
    const auto permission=extensionPermissions_.find(item);
    const bool extensionAllowed=permission!=extensionPermissions_.end()&&permission->second.variants.count(id)!=0;
    require(l3||l12||triplet||sextuplet||extensionAllowed,"This app version has no reviewed runtime permission for the selected variant; keep reading its instructions.");
    const Rational step=extensionAllowed?permission->second.step:l3?Rational{1,4}:l12?Rational{1,2}:triplet?Rational{1,3}:Rational{1,6};
    const std::size_t count=extensionAllowed?permission->second.eventCount:l3?20:l12?16:3;
    const auto& model=v.model->source();
    require(!model.syntheticFixture&&model.itemId==item&&model.events.size()==count&&model.measures.empty()
        &&model.instrument.openMidi==std::vector<int>({40,45,50,55,59,64})&&model.instrument.capo==0,"Runtime selection differs from its reviewed event/setup scope");
    for(std::size_t i=0;i<count;++i){const auto& event=model.events[i];
        const Rational expected=installedCaseOnset(step,i,
            extensionAllowed?permission->second.gapAfterEvent:0,
            extensionAllowed?permission->second.gapDuration:Rational{0},
            extensionAllowed?permission->second.secondGapAfterEvent:0,
            extensionAllowed?permission->second.secondGapDuration:Rational{0});
        require(event.kind==music::Kind::Note&&event.span.onset==expected&&event.span.duration==step
            &&event.tones.size()==1&&event.tones.front().attack==music::Attack::Picked&&event.tones.front().tieFrom.empty(),"Selected reference requires its exact reviewed picked-note span; unsupported timing or articulation cannot be substituted");
    }
    const Rational span=*model.events.back().span.onset+*model.events.back().span.duration;
    J::Object hashes;for(const auto& ref:at(l.record,"source_refs").array())hashes.emplace(ref.string(),at(at(package_,"sources"),ref.string()).object().at("sha256"));
    J identity=J::Object{{"runtime_permission","lesson-runtime.1"},{"bundle_sha256",manifestHash_},{"decision_sha256",decisionHash_},{"package_sha256",packageHash_},
        {"item_id",item},{"variant_id",id},{"workbook_id",at(l.record,"workbook_id")},{"legacy_level",at(l.record,"legacy_level")},{"content_revision",at(l.record,"content_revision")},{"content_version",contentVersion_},
        {"source_manifest_sha256",at(package_,"source_manifest_sha256")},{"source_refs",at(l.record,"source_refs")},{"source_hashes",hashes},
        {"scope",at(l.record,"control_scope")},{"practice_allowed",l3||l12||extensionAllowed},{"whole_task_completion",false},
        {"span",J::Array{J::fromInteger(span.numerator()),J::fromInteger(span.denominator())}},
        {"authored_practice_guidance",at(l.record,"authored_text_refs")}};
    const std::string description=extensionAllowed?permission->second.description:l3?"One selected 20-note direction. This is not the complete ascending/descending, both-pick-start source task.":l12?"One connected 16-note cell. This is not the moving ladder or its complete round trip.":"Three-note illustration only. The authored rolling sequence must continue; do not repeat or resume this excerpt as a Practice task.";
    return std::shared_ptr<const Admission>(new Admission(v.model,std::move(identity),span,l3||l12||extensionAllowed,description));
}
std::shared_ptr<const Admission> Catalog::admitCell(const std::string& item,const std::string& id,std::uint32_t ordinal) const {
    require(item=="fg:item:000002"&&ordinal>=1&&ordinal<=5,
        "Choose transfer cell 1–5 of a supported Level 3 direction. Other lessons and arbitrary cutpoints require their complete supported span.");
    const auto parent=admit(item,id); // Enforces the exact reviewed variant, source and articulation scope.
    const auto& source=parent->model()->source();
    const auto begin=static_cast<std::size_t>(ordinal-1)*4;
    music::Model projection=source;
    projection.events.assign(source.events.begin()+static_cast<std::ptrdiff_t>(begin),
                             source.events.begin()+static_cast<std::ptrdiff_t>(begin+4));
    J::Array ids;
    for(std::size_t i=0;i<projection.events.size();++i){
        auto& event=projection.events[i];
        // The parent proves contiguous quarter fractions and picked attacks.
        // Secondary member/contact spans cannot be silently shifted or cut.
        require(!event.tones.front().memberSpan&&!event.tones.front().soundingSpan,
            "This transfer cell has an unsupported secondary articulation span; use its full direction.");
        event.span.onset=Rational{static_cast<std::int64_t>(i),4};ids.emplace_back(event.id);
    }
    const auto validated=music::validate(projection);
    require(validated.validReference(),"Selected transfer cell failed musical projection validation; retain the source and use its full direction.");
    const Rational origin{static_cast<std::int64_t>(ordinal-1)};
    const auto num=[](std::int64_t x){return J::fromInteger(x);};
    J identity=parent->identity();
    identity.object()["span"]=J::Array{num(1),num(1)};
    identity.object()["selection"]=J::Object{{"version","lesson-transfer-cell.1"},{"ordinal",num(ordinal)},
        {"parent_source_binding",parent->sourceBinding()},
        {"source_span",J::Object{{"start",J::Array{num(ordinal-1),num(1)}},{"end",J::Array{num(ordinal),num(1)}}}},
        {"event_ids",std::move(ids)},{"timeline","local_zero_from_source_start"}};
    const auto description="Selected four-note transfer cell "+std::to_string(ordinal)+" of 5 in this direction. This is not a bar, a complete direction or the complete source task. Follow the unchanged source instructions.";
    return std::shared_ptr<const Admission>(new Admission(validated.model,std::move(identity),Rational{1},true,description,origin));
}
std::string readinessText(const Variant& v){
    std::string s=v.model->source().events.empty()?"This task has no authored note events. Read and carry out the task instructions.":v.technicallyRenderable?"The selected notation has complete reference timing. Available playback depends on the supported selected span; reading or playback does not complete the source task.":"Read the selected notation and instructions. Reference playback is unavailable for this variant.";
    for(const auto& reason:v.limitations)s+="\n"+reason;
    return s;
}
std::string Catalog::text(const std::string& item,const std::string& variantId,Section section) const {
    const auto owner=extensions_.find(item);
    if(owner!=extensions_.end())return owner->second->text(item,variantId,section);
    const auto& l=lesson(item);const auto& v=variant(item,variantId);const auto& r=l.record;
    const std::string extent="Selected control case only: "+at(at(r,"control_scope"),"local_case").string()+"\nThis is not the complete workbook. Reading or playback does not complete the task.\n\n";
    switch(section){
    case Section::Instructions:{
        std::string out=extent;std::vector<std::string> refs;std::set<std::string> seen;
        for(const auto* list:{&at(r,"authored_text_refs"),&at(at(r,"control_scope"),"basis_refs")})for(const auto& ref:list->array())if(seen.insert(ref.string()).second)refs.push_back(ref.string());
        for(const auto& id:refs){const auto& source=at(at(package_,"sources"),id);out+=id+" — "+at(source,"path").string();if(at(source,"format").string()=="pdf")out+=" · page "+json::stringify(at(source,"page"));else out+=" · lines "+json::stringify(at(source,"first_line"))+"–"+json::stringify(at(source,"last_line"));out+="\n\n"+at(source,"text").string()+"\n\n";}
        return out;}
    case Section::Context:return extent+"Source context\n"+display(at(r,"context"))+"\nNormalization and preserved historical representation notes\nThese are separate from the source instructions; older candidate-status wording is retained for provenance. The selected conversion is now accepted for this reader.\n"+display(at(r,"normalization"))+"\nUnresolved source/configuration limits\n"+display(at(r,"ambiguities"));
    case Section::Assessment:return extent+(at(r,"rubric").null()?"No scored rubric is specified for this selected case. Follow its source practice/advance instructions.\n":"Source rubric — explicit learner/reviewer attestations; no automatic scoring. All dimensions, protected conditions, artifacts and repeatability remain required.\n\n"+display(at(r,"rubric")))+"\nFull authored requirements remain in Source instructions. Clean or scheduled cycles cannot replace them.\n";
    case Section::Resources:{std::string out=extent+"Offline resources\nAn unavailable required resource leaves that task incomplete; browsing and other practice remain available. No media, partner, recorder, importer or redistribution rights are supplied by this preview.\n\n";if(l.resources.empty())out+="No external-resource plan entry is attached to this selected level. Follow the source instructions for its task conditions.\n";for(const auto& res:l.resources)out+=display(res)+"\n";return out;}
    case Section::VariantDetails:return extent+readinessText(v)+"\n\nSelected source variant\n"+display(v.authored)+"\nStable lesson identity: "+l.id+"\nContent version: "+contentVersion_+"\n";
    }
    throw std::invalid_argument("Unknown lesson section");
}
}
